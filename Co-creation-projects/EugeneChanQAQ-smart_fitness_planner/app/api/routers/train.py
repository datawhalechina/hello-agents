from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ...models.schemas import (
    FitnessRequest,
    FitnessResponse,
    ErrorResponse
)
from ...agents.train_planner import get_fitness_planner_agent

router = APIRouter(prefix="/train", tags=["训练计划"])

# 前端界面HTML
TRAINING_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>健身计划生成器</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }

        .content {
            padding: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }

        input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input:focus {
            outline: none;
            border-color: #667eea;
        }

        .input-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 1.1em;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
            transition: transform 0.2s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .result {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            display: none;
        }

        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error {
            background: #ffe6e6;
            color: #d63031;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }

        .plan-details {
            margin-top: 15px;
        }

        .plan-item {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 3px solid #764ba2;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏋️ 健身计划生成器</h1>
            <p>输入您的身体信息，获取个性化的训练计划</p>
        </div>

        <div class="content">
            <div class="form-group">
                <label>基本信息</label>
                <div class="input-row">
                    <div>
                        <label for="height">身高 (cm)</label>
                        <input type="number" id="height" placeholder="例如: 183" min="100" max="250">
                    </div>
                    <div>
                        <label for="weight">体重 (kg)</label>
                        <input type="number" id="weight" placeholder="例如: 76" min="30" max="200">
                    </div>
                    <div>
                        <label for="age">年龄</label>
                        <input type="number" id="age" placeholder="例如: 26" min="12" max="80">
                    </div>
                </div>
            </div>

            <button class="btn" onclick="generatePlan()">
                🏋️ 生成训练计划
            </button>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在生成个性化的训练计划...</p>
            </div>

            <div class="error" id="error"></div>

            <div class="result" id="result">
                <!-- 结果将在这里动态显示 -->
            </div>
        </div>
    </div>

    <script>
        async function generatePlan() {
            // 获取输入值
            const height = document.getElementById('height').value;
            const weight = document.getElementById('weight').value;
            const age = document.getElementById('age').value;

            // 验证输入
            if (!height || !weight || !age) {
                showError('请填写所有基本信息');
                return;
            }

            if (height < 100 || height > 250) {
                showError('请输入合理的身高 (100-250cm)');
                return;
            }

            if (weight < 30 || weight > 200) {
                showError('请输入合理的体重 (30-200kg)');
                return;
            }

            if (age < 12 || age > 80) {
                showError('请输入合理的年龄 (12-80岁)');
                return;
            }

            // 显示加载中
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('error').style.display = 'none';

            try {
                const response = await fetch('/train/plan', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        height: parseInt(height),
                        weight: parseInt(weight),
                        age: parseInt(age)
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || '请求失败');
                }

                if (data.success) {
                    displayResult(data);
                } else {
                    showError(data.message || '生成训练计划失败');
                }
            } catch (error) {
                showError('请求错误: ' + error.message);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        function displayResult(response) {
            const resultDiv = document.getElementById('result');
            const planList = response.fitness_plan; // 现在是列表
        
            let html = `<h3>🎉 您的个性化训练计划</h3>
                        <div class="plan-details">`;
        
            // 循环显示每一天的训练计划
            planList.forEach((plan) => {
                html += `
                    <div class="plan-item">
                        <h4>📅 第 ${plan.day} 天</h4>
                        <p><strong>训练动作:</strong> ${plan.action}</p>
                        <p><strong>目标肌肉群:</strong> ${plan.muscle ? plan.muscle : '休息'}</p>
                        <p><strong>组数:</strong> ${plan.group_num !== null ? plan.group_num : '-'}</p>
                        <p><strong>每组数量:</strong> ${plan.amount !== null ? plan.amount : '-'}</p>
                    </div>
                `;
            });
        
            html += `</div>
                     <p style="margin-top: 15px; color: #666;">
                        <strong>提示:</strong> 这是一个基于您身体数据生成的个性化训练计划，请根据自身情况适当调整。
                     </p>`;
        
            resultDiv.innerHTML = html;
            resultDiv.style.display = 'block';
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }

        // 回车键提交
        document.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                generatePlan();
            }
        });
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def training_page():
    """训练计划生成器页面"""
    return TRAINING_HTML

@router.post(
    "/plan",
    response_model=FitnessResponse,
    summary="生成训练计划",
    description="根据用户的基本情况生成训练计划"
)

async def plan_train(request: FitnessRequest):
    """
    生成训练计划
    :param request: 训练请求参数（个人基本数据）
    :return:训练计划建议
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 收到训练计划制定请求:")
        print(f"   身高: {request.height}")
        print(f"   体重: {request.weight}")
        print(f"   年龄: {request.age}")
        print(f"{'='*60}\n")

        # 获取agent实例
        print("获取Agent系统")
        agent = get_fitness_planner_agent()

        # 开始生成健身计划
        train_plan = agent.plan_train(request)

        print("✅ 训练计划生成成功,准备返回响应\n")

        return FitnessResponse(
            success=True,
            message="训练计划生成成功",
            fitness_plan=train_plan
        )

    except Exception as e:
        print(f"❌ 生成训练计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成训练计划失败: {str(e)}"
        )