"""
分析相关API路由
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
import arxiv
import os
from core.config import get_config
from core.llm_adapter import get_llm_adapter
from utils.pdf_parser import pdf_parser

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化 LLM 适配器（基于 HelloAgent）
config = get_config()
try:
    llm = get_llm_adapter() if config.llm.api_key else None
except Exception as e:
    logger.warning(f"LLM 初始化失败: {str(e)}")
    llm = None

# Pydantic模型
class AnalysisRequest(BaseModel):
    paper_id: str
    user_id: Optional[str] = None
    analysis_type: str = "full"  # full, quick, innovation_only

class ComparisonRequest(BaseModel):
    paper_ids: List[str]
    user_id: Optional[str] = None
    comparison_aspects: List[str] = ["method", "results", "innovation"]

class InnovationSearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    search_scope: str = "both"  # l1, l2, both
    top_k: int = 10

class PaperAnalysisRequest(BaseModel):
    paper_url: str
    analysis_type: str = "summary"  # summary, innovation, comparison, comprehensive

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_paper(request: PaperAnalysisRequest):
    """分析论文 - 支持 ArXiv URL 和本地 PDF 文件"""
    try:
        if not llm:
            raise HTTPException(status_code=503, detail="AI 服务未配置，请设置 OPENAI_API_KEY")
        
        import re
        paper_url = request.paper_url.strip()
        
        # 检查是否是本地上传的 PDF 文件
        if paper_url.startswith('/uploads/') or paper_url.endswith('.pdf'):
            logger.info(f"检测到本地 PDF 文件: {paper_url}")
            
            # 构建完整的文件路径
            if paper_url.startswith('/uploads/'):
                # Sanitize filename to prevent path traversal
                safe_name = os.path.basename(paper_url)
                if not safe_name or not safe_name.endswith('.pdf'):
                    raise HTTPException(status_code=400, detail="无效的文件名")
                file_path = os.path.join('downloads', safe_name)
            else:
                # For non-upload paths, also sanitize to prevent arbitrary file access
                safe_name = os.path.basename(paper_url)
                if not safe_name or not safe_name.endswith('.pdf'):
                    raise HTTPException(status_code=400, detail="无效的文件名")
                file_path = os.path.join('downloads', safe_name)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"PDF 文件不存在: {file_path}")
                raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {paper_url}")
            
            # 解析 PDF 文件
            logger.info(f"开始解析 PDF 文件: {file_path}")
            pdf_result = await pdf_parser.parse_pdf(file_path)
            
            if not pdf_result.get("success"):
                raise HTTPException(status_code=500, detail=pdf_result.get("error", "PDF 解析失败"))
            
            # 使用解析出的内容进行 AI 分析
            title = pdf_result.get("title", "未知标题")
            authors = pdf_result.get("authors", ["未知作者"])
            abstract = pdf_result.get("abstract", "")
            full_text = pdf_result.get("full_text", "")
            
            # 限制文本长度以避免超出 token 限制
            text_for_analysis = full_text[:8000] if len(full_text) > 8000 else full_text
            
            # 根据分析类型生成提示词
            prompts = {
                "summary": f"""请对以下论文进行摘要分析：

标题：{title}
作者：{', '.join(authors)}
摘要：{abstract}

论文内容（前8000字符）：
{text_for_analysis}

请提供：
1. 研究背景和动机
2. 主要方法
3. 核心贡献
4. 实验结果
5. 研究意义

请用中文回答，保持专业和简洁。""",
                
                "innovation": f"""请分析以下论文的创新点：

标题：{title}
摘要：{abstract}

论文内容：
{text_for_analysis}

请详细分析：
1. 技术创新点
2. 方法论创新
3. 理论贡献
4. 与现有工作的区别
5. 潜在应用价值

请用中文回答。""",
                
                "comparison": f"""请对以下论文进行对比分析：

标题：{title}
摘要：{abstract}

论文内容：
{text_for_analysis}

请分析：
1. 与传统方法的对比
2. 优势和劣势
3. 适用场景
4. 性能提升
5. 局限性

请用中文回答。""",
                
                "comprehensive": f"""请对以下论文进行全面综合分析：

标题：{title}
作者：{', '.join(authors)}
摘要：{abstract}

论文内容：
{text_for_analysis}

请提供全面的分析，包括：
1. 研究背景和意义
2. 技术方法详解
3. 创新点分析
4. 实验验证
5. 优缺点评价
6. 未来研究方向
7. 实际应用价值

请用中文回答，保持专业和深度。"""
            }
            
            prompt = prompts.get(request.analysis_type, prompts["summary"])
            
            # 调用 LLM 进行分析
            logger.info(f"开始 AI 分析，类型: {request.analysis_type}")
            response = await llm.ainvoke(prompt)
            analysis_content = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "success": True,
                "paper_info": {
                    "id": "local_pdf",
                    "title": title,
                    "authors": authors,
                    "published_date": "N/A",
                    "url": paper_url,
                    "categories": ["本地文件"],
                    "page_count": pdf_result.get("page_count", 0),
                    "word_count": pdf_result.get("word_count", 0)
                },
                "analysis_type": request.analysis_type,
                "analysis": analysis_content,
                "abstract": abstract
            }
        
        # ArXiv 论文处理
        arxiv_patterns = [
            r'arxiv\.org/abs/(\d+\.\d+)',
            r'arxiv\.org/pdf/(\d+\.\d+)',
            r'arXiv:(\d+\.\d+)',
            r'\[(\d+\.\d+)v?\d*\]',
            r'^(\d{4}\.\d{4,5})v?\d*$'
        ]
        
        paper_id = None
        for pattern in arxiv_patterns:
            match = re.search(pattern, paper_url, re.IGNORECASE)
            if match:
                paper_id = match.group(1)
                break
        
        if not paper_id:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的输入。支持的格式：\n" +
                       "- ArXiv URL: https://arxiv.org/abs/2511.16672\n" +
                       "- ArXiv ID: 2511.16672\n" +
                       "- 本地 PDF: 上传后自动填充"
            )
        
        logger.info(f"正在分析 ArXiv 论文: {paper_id}")
        
        # 获取论文信息
        search = arxiv.Search(id_list=[paper_id])
        paper = next(search.results(), None)
        
        if not paper:
            raise HTTPException(status_code=404, detail=f"未找到 ArXiv 论文: {paper_id}")
        
        # 根据分析类型生成提示词
        prompts = {
            "summary": f"""请对以下论文进行摘要分析：

标题：{paper.title}
作者：{', '.join([a.name for a in paper.authors])}
摘要：{paper.summary}

请提供：
1. 研究背景和动机
2. 主要方法
3. 核心贡献
4. 实验结果
5. 研究意义

请用中文回答，保持专业和简洁。""",
            
            "innovation": f"""请分析以下论文的创新点：

标题：{paper.title}
摘要：{paper.summary}

请详细分析：
1. 技术创新点
2. 方法论创新
3. 理论贡献
4. 与现有工作的区别
5. 潜在应用价值

请用中文回答。""",
            
            "comparison": f"""请对以下论文进行对比分析：

标题：{paper.title}
摘要：{paper.summary}

请分析：
1. 与传统方法的对比
2. 优势和劣势
3. 适用场景
4. 性能提升
5. 局限性

请用中文回答。""",
            
            "comprehensive": f"""请对以下论文进行全面综合分析：

标题：{paper.title}
作者：{', '.join([a.name for a in paper.authors])}
摘要：{paper.summary}
分类：{', '.join(paper.categories)}

请提供全面的分析，包括：
1. 研究背景和意义
2. 技术方法详解
3. 创新点分析
4. 实验验证
5. 优缺点评价
6. 未来研究方向
7. 实际应用价值

请用中文回答，保持专业和深度。"""
        }
        
        prompt = prompts.get(request.analysis_type, prompts["summary"])
        
        # 调用 LLM 进行分析
        response = await llm.ainvoke(prompt)
        analysis_content = response.content if hasattr(response, 'content') else str(response)
        
        return {
            "success": True,
            "paper_info": {
                "id": paper_id,
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "published_date": paper.published.strftime("%Y-%m-%d"),
                "url": paper.entry_id,
                "categories": paper.categories
            },
            "analysis_type": request.analysis_type,
            "analysis": analysis_content,
            "abstract": paper.summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"论文分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@router.post("/compare", response_model=Dict[str, Any])
async def compare_papers(request: ComparisonRequest):
    """对比多篇论文"""
    try:
        # 这里需要实现论文对比逻辑
        # 暂时返回模拟结果
        
        comparison_result = {
            "paper_ids": request.paper_ids,
            "comparison_aspects": request.comparison_aspects,
            "similarities": ["相似点1", "相似点2"],
            "differences": ["差异点1", "差异点2"],
            "innovation_gaps": ["创新空白1", "创新空白2"],
            "recommendations": ["建议1", "建议2"]
        }
        
        return {
            "success": True,
            "result": comparison_result
        }
        
    except Exception as e:
        logger.error(f"论文对比失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/innovation/search", response_model=Dict[str, Any])
async def search_innovation_opportunities(request: InnovationSearchRequest):
    """搜索创新机会"""
    try:
        # 这里需要实现创新机会搜索逻辑
        # 暂时返回模拟结果
        
        innovation_results = {
            "query": request.query,
            "opportunities": [
                {
                    "title": "创新机会1",
                    "description": "基于当前研究的创新方向",
                    "related_papers": ["paper1", "paper2"],
                    "confidence": 0.85
                },
                {
                    "title": "创新机会2", 
                    "description": "另一个潜在的研究方向",
                    "related_papers": ["paper3", "paper4"],
                    "confidence": 0.72
                }
            ],
            "research_gaps": ["研究空白1", "研究空白2"],
            "future_directions": ["未来方向1", "未来方向2"]
        }
        
        return {
            "success": True,
            "result": innovation_results
        }
        
    except Exception as e:
        logger.error(f"创新机会搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/paper/{paper_id}/summary")
async def get_paper_summary(paper_id: str, user_id: Optional[str] = None):
    """获取论文摘要"""
    try:
        # 这里需要实现论文摘要生成逻辑
        # 暂时返回模拟结果
        
        summary = {
            "paper_id": paper_id,
            "summary": "这是一篇关于...的论文，主要贡献包括...",
            "key_contributions": ["贡献1", "贡献2", "贡献3"],
            "methodology": "论文采用的方法是...",
            "results": "实验结果表明...",
            "limitations": "研究的局限性包括...",
            "future_work": "未来工作方向..."
        }
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"获取论文摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/paper/{paper_id}/innovations")
async def get_paper_innovations(paper_id: str, user_id: Optional[str] = None):
    """获取论文创新点"""
    try:
        # 这里需要实现创新点提取逻辑
        # 暂时返回模拟结果
        
        innovations = {
            "paper_id": paper_id,
            "innovations": [
                {
                    "aspect": "方法创新",
                    "description": "提出了新的方法...",
                    "novelty": "high",
                    "impact": "significant"
                },
                {
                    "aspect": "理论创新", 
                    "description": "在理论上有所突破...",
                    "novelty": "medium",
                    "impact": "moderate"
                }
            ],
            "comparison_with_prior_work": "与之前的工作相比...",
            "potential_applications": ["应用1", "应用2"]
        }
        
        return {
            "success": True,
            "innovations": innovations
        }
        
    except Exception as e:
        logger.error(f"获取论文创新点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}/insights")
async def get_user_insights(user_id: str):
    """获取用户研究洞察"""
    try:
        # 这里需要实现用户研究洞察分析
        # 暂时返回模拟结果
        
        insights = {
            "user_id": user_id,
            "research_interests": ["兴趣1", "兴趣2"],
            "reading_patterns": {
                "papers_read": 50,
                "favorite_topics": ["主题1", "主题2"],
                "reading_frequency": "daily"
            },
            "knowledge_gaps": ["知识空白1", "知识空白2"],
            "research_suggestions": [
                {
                    "topic": "建议研究方向1",
                    "reason": "基于您的阅读历史...",
                    "related_papers": ["paper1", "paper2"]
                }
            ],
            "skill_assessment": {
                "technical_skills": ["技能1", "技能2"],
                "writing_skills": ["写作技能1", "写作技能2"],
                "improvement_areas": ["改进领域1", "改进领域2"]
            }
        }
        
        return {
            "success": True,
            "insights": insights
        }
        
    except Exception as e:
        logger.error(f"获取用户研究洞察失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=Dict[str, Any])
async def batch_analyze_papers(paper_ids: List[str], user_id: Optional[str] = None):
    """批量分析论文"""
    try:
        results = []
        
        for paper_id in paper_ids:
            try:
                # 提交论文分析任务
                task_id = await agent_controller.submit_task(
                    TaskType.PAPER_ANALYSIS,
                    {
                        "paper_id": paper_id,
                        "user_id": user_id,
                        "analysis_type": "quick"  # 批量分析使用快速模式
                    }
                )
                
                # 执行任务
                result = await agent_controller.execute_task(task_id)
                
                results.append({
                    "paper_id": paper_id,
                    "task_id": task_id,
                    "success": True,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "paper_id": paper_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_papers": len(paper_ids),
            "successful_analyses": sum(1 for r in results if r["success"]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"批量分析论文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-pdf", response_model=Dict[str, Any])
async def upload_pdf_for_analysis(file: UploadFile = File(...)):
    """
    上传 PDF 文件并解析
    返回文件信息和解析结果
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持 PDF 文件")
        
        # 读取文件内容
        logger.info(f"接收到 PDF 文件: {file.filename}")
        pdf_bytes = await file.read()
        
        # 解析 PDF
        pdf_result = await pdf_parser.parse_pdf_from_bytes(pdf_bytes, file.filename)
        
        if not pdf_result.get("success"):
            raise HTTPException(status_code=500, detail=pdf_result.get("error", "PDF 解析失败"))
        
        # 保存文件到 downloads 目录
        os.makedirs("downloads", exist_ok=True)
        safe_filename = os.path.basename(file.filename)
        if not safe_filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        file_path = os.path.join("downloads", safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        
        logger.info(f"PDF 文件已保存: {file_path}")
        
        return {
            "success": True,
            "filename": safe_filename,
            "file_path": f"/uploads/{safe_filename}",
            "title": pdf_result.get("title", "未知标题"),
            "authors": pdf_result.get("authors", ["未知作者"]),
            "abstract": pdf_result.get("abstract", "")[:500],  # 限制摘要长度
            "page_count": pdf_result.get("page_count", 0),
            "word_count": pdf_result.get("word_count", 0),
            "message": "PDF 文件上传并解析成功，可以使用返回的 file_path 进行分析"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF 上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
