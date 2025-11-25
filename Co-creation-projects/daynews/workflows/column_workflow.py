import time
import Agently
from .tools.search import search
from .tools.browse import browse

def start(column_outline, *, agent_factory, SETTINGS, root_path, logger):
    tool_proxy = (
        SETTINGS.TOOL_PROXY
        if hasattr(SETTINGS, "TOOL_PROXY")
        else
        (
            SETTINGS.PROXY
            if hasattr(SETTINGS, "PROXY")
            else None
        ) 
    )
    logger.info("[Start Generate Column]", column_outline["column_title"])
    column_workflow = Agently.Workflow()
    column_editor_agent = agent_factory.create_agent()
    # You can set column editor agent here, read https://github.com/Maplemx/Agently/tree/main/docs/guidebook to explore
    """
    (
        column_editor_agent
            .set_role("...")
            .set_user_info("...")
    )
    """

    # Define Workflow Chunks
    @column_workflow.chunk("start", type="Start")

    @column_workflow.chunk("search")
    def search_executor(inputs, storage):
        storage.set(
            "searched_news",
            search(
                column_outline["search_keywords"],
                timelimit=SETTINGS.NEWS_TIME_LIMIT if hasattr(SETTINGS, "NEWS_TIME_LIMIT") else "d",
                proxy=tool_proxy,
                logger=logger,
            )
        )

    @column_workflow.chunk("pick_news")
    def pick_news_executor(inputs, storage):
        searched_news = storage.get("searched_news", [])
        logger.info("[Search News Count]", len(searched_news))
        if len(searched_news) > 0:
            pick_results = (
                column_editor_agent
                    .load_yaml_prompt(
                        path=f"{ root_path }/prompts/pick_news.yaml",
                        variables={
                            "column_news": searched_news,
                            "column_requirement": column_outline["column_requirement"],
                        }
                    )
                    .start()
            )
            # sleep to avoid requesting too often
            time.sleep(SETTINGS.SLEEP_TIME)
            picked_news = []
            for pick_result in pick_results:
                if pick_result["can_use"]:
                    news = searched_news[int(pick_result["id"])].copy()
                    news.update({ "recommend_comment": pick_result["recommend_comment"] })
                    picked_news.append(news)
            storage.set("picked_news", picked_news)
            logger.info("[Picked News Count]", len(picked_news))
        else:
            storage.set("picked_news", [])
            logger.info("[Picked News Count]", 0)

    @column_workflow.chunk("read_and_summarize")
    def read_and_summarize_executor(inputs, storage):
        picked_news = storage.get("picked_news", [])
        readed_news = []
        if picked_news and len(picked_news) > 0:
            for news in picked_news:
                logger.info("[Summarzing]", news["title"])
                news_content = browse(
                    news["url"],
                    proxy=tool_proxy,
                    logger=logger,
                )
                if news_content and news_content != "":
                    try:
                        summary_result = (
                            column_editor_agent
                                .load_yaml_prompt(
                                    path=f"{ root_path }/prompts/summarize.yaml",
                                    variables={
                                        "news_content": news_content,
                                        "column_requirement": column_outline["column_requirement"],
                                        "news_title": news["title"],
                                        "language": SETTINGS.OUTPUT_LANGUAGE,
                                    }
                                )
                                .start()
                        )
                        if summary_result["can_summarize"]:
                            readed_news_info = news.copy()
                            readed_news_info.update({
                                "title": summary_result["translated_title"],
                                "summary": summary_result["summary"]
                            })
                            readed_news.append(readed_news_info)
                            logger.info("[Summarzing]", "Success")
                        else:
                            logger.info("[Summarzing]", "Failed")
                        # sleep to avoid requesting too often
                        time.sleep(SETTINGS.SLEEP_TIME)
                    except Exception as e:
                        logger.error(f"[Summarzie]: Can not summarize '{ news['title'] }'.\tError: { str(e) }")
        storage.set("readed_news", readed_news)

    @column_workflow.chunk("write_column")
    def write_column_executor(inputs, storage):
        readed_news = storage.get("readed_news", [])
        if readed_news and len(readed_news) > 0:
            slimmed_news = []
            for index, news in enumerate(readed_news):
                slimmed_news.append({
                    "id": index,
                    "title": news["title"],
                    "summary": news["summary"],
                    "url": news["url"],
                })
            column_result = (
                column_editor_agent
                    .load_yaml_prompt(
                        path=f"{ root_path }/prompts/write_column.yaml",
                        variables={
                            "slimmed_news": slimmed_news,
                            "column_requirement": column_outline["column_requirement"],
                            "language": SETTINGS.OUTPUT_LANGUAGE,
                        }
                    )
                    .start()
            )
            # sleep to avoid requesting too often
            time.sleep(SETTINGS.SLEEP_TIME)
            final_news_list = []
            for news in column_result["news_list"]:
                id = news["id"]
                final_news_list.append({
                    "url": readed_news[id]["url"],
                    "title": readed_news[id]["title"],
                    "summary": readed_news[id]["summary"],
                    "recommend_comment": news["recommend_comment"],
                })
            storage.set("final_result", {
                "title": column_outline["column_title"],
                "prologue": column_result["prologue"],
                "news_list": final_news_list,
            })
        else:
            storage.set("final_result", None)

    # Connect Chunks
    (
        column_workflow.chunks["start"]
            .connect_to(column_workflow.chunks["search"])
            .connect_to(column_workflow.chunks["pick_news"])
            .connect_to(column_workflow.chunks["read_and_summarize"])
            .connect_to(column_workflow.chunks["write_column"])
    )

    # Start Workflow
    column_workflow.start()

    return column_workflow.executor.store.get("final_result")
