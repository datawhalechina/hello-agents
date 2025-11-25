import time
import Agently
from datetime import datetime
from .column_workflow import start as start_column_workflow

def start(*, agent_factory, SETTINGS, root_path, logger):
    main_workflow = Agently.Workflow()
    chief_editor_agent = agent_factory.create_agent()
    # You can set chief editor agent here, read https://github.com/Maplemx/Agently/tree/main/docs/guidebook to explore
    """
    (
        chief_editor_agent
            .set_role("...")
            .set_user_info("...")
    )
    """

    # Define Workflow Chunks
    @main_workflow.chunk("start", type="Start")

    @main_workflow.chunk("input_topic")
    def input_topic_executor(inputs, storage):
        if not SETTINGS.USE_CUSTOMIZE_OUTLINE:
            storage.set(
                "topic",
                input("[Please input the topic of your news collection]: ")
            )

    @main_workflow.chunk("generate_outline")
    def generate_outline_executor(inputs, storage):
        if SETTINGS.USE_CUSTOMIZE_OUTLINE:
            storage.set("outline", SETTINGS.CUSTOMIZE_OUTLINE)
            logger.info("[Use Customize Outline]", SETTINGS.CUSTOMIZE_OUTLINE)
        else:
            # Load prompt from /prompts/create_outline.yaml
            try:
                logger.info("[Generating Outline] Topic:", storage.get("topic"))
                outline = (
                    chief_editor_agent
                        .load_yaml_prompt(
                            path=f"{ root_path }/prompts/create_outline.yaml",
                            variables={
                                "topic": storage.get("topic"),
                                "news_time_limit": SETTINGS.NEWS_TIME_LIMIT if hasattr(SETTINGS, "NEWS_TIME_LIMIT") else "d",
                                "language": SETTINGS.OUTPUT_LANGUAGE,
                                "max_column_num": SETTINGS.MAX_COLUMN_NUM,
                            }
                        )
                        .start()
                )
                storage.set("outline", outline)
                logger.info("[Outline Generated]", outline)
                # sleep to avoid requesting too often
                time.sleep(SETTINGS.SLEEP_TIME)
            except Exception as e:
                logger.error(f"[Outline Generation Failed] Error: {str(e)}")
                logger.error(f"[Suggestion] Please check:")
                logger.error(f"  1. API Key is valid: {SETTINGS.MODEL_AUTH.get('api_key', 'N/A')[:20]}...")
                logger.error(f"  2. API URL is correct: {SETTINGS.MODEL_URL if hasattr(SETTINGS, 'MODEL_URL') else 'N/A'}")
                logger.error(f"  3. Model name is valid: {SETTINGS.MODEL_OPTIONS.get('model', 'N/A')}")
                logger.error(f"  4. Network connection is working")
                raise Exception(f"Failed to generate outline: {str(e)}")

    @main_workflow.chunk("generate_columns")
    def generate_columns_executor(inputs, storage):
        columns_data = []
        outline = storage.get("outline")
        for column_outline in outline["column_list"]:
            column_data = start_column_workflow(
                column_outline=column_outline,
                agent_factory=agent_factory,
                SETTINGS=SETTINGS,
                root_path=root_path,
                logger=logger,
            )
            if column_data:
                columns_data.append(column_data)
                logger.info("[Column Data Prepared]", column_data)
        storage.set("columns_data", columns_data)

    @main_workflow.chunk("generate_markdown")
    def generate_markdown_executor(inputs, storage):
        outline = storage.get("outline")
        columns_data = storage.get("columns_data")
        if columns_data and len(columns_data) > 0:
            # Main Title
            md_doc_text = f'# { outline["report_title"] }\n\n'
            md_doc_text += f'> { datetime.now().strftime("%Y-%m-%d %A") }\n\n'
            # Columns
            if SETTINGS.IS_DEBUG:
                logger.debug("[Columns Data]", columns_data)
            for column_data in columns_data:
                md_doc_text += f'## { column_data["title"] }\n\n### PROLOGUE\n\n'
                md_doc_text += f'> { column_data["prologue"] }\n\n'
                md_doc_text += f"### NEWS LIST\n\n"
                for single_news in column_data["news_list"]:
                    md_doc_text += f'- [{ single_news["title"] }]({ single_news["url"] })\n\n'
                    md_doc_text += f'    - `[summray]` { single_news["summary"] }\n'
                    md_doc_text += f'    - `[comment]` { single_news["recommend_comment"] }\n\n'
            # Tailer
            md_doc_text +="\n\n---\n\nPowered by [Agently AI Application Development Framework & Agently Workflow](https://github.com/Maplemx/Agently)\n\n"
            md_doc_text += f"Model Information：{ SETTINGS.MODEL_PROVIDER if hasattr(SETTINGS, 'MODEL_PROVIDER') else 'OpenAI' } - { str(SETTINGS.MODEL_OPTIONS) if hasattr(SETTINGS, 'MODEL_OPTIONS') else 'Default Options' }\n\n"
            md_doc_text += '**_<font color = "red">Agent</font><font color = "blue">ly</font>_** [Guidebook](https://github.com/Maplemx/Agently/blob/main/docs/guidebook)\n\n[Apply Developers WeChat Group](https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf) or Scan QR Code to Apply.\n\n<img width="120" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/7f4bc9bf-a125-4a1e-a0a4-0170b718c1a6">'
            logger.info("[Markdown Generated]", md_doc_text)
            with open(f'{ root_path }/{ outline["report_title"] }_{ datetime.now().strftime("%Y-%m-%d") }.md', 'w', encoding='utf-8') as f:
                f.write(md_doc_text)
        else:
            logger.info("[Markdown Generation Failed] Due to have not any column data.")

    # Connect Chunks
    (
        main_workflow.chunks["start"]
            .connect_to(main_workflow.chunks["input_topic"])
            .connect_to(main_workflow.chunks["generate_outline"])
            .connect_to(main_workflow.chunks["generate_columns"])
            .connect_to(main_workflow.chunks["generate_markdown"])
    )

    # Start Workflow
    main_workflow.start()