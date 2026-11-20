from hello_agents.tools import Tool,tool_action



class DataAnalysisTool(Tool):

    def __init__(self):
        super().__init__("data_analysis", "数据分析工具集", expandable=True)
        self.data = None
        self.report_sections = []

    @tool_action("load_data", "加载 CSV/XLSX 数据文件")
    def _load_data(self, file_path: str) -> str:
        '''加载数据文件并保存为会话 DataFrame

        Args:
            file_path: 数据文件路径，支持 CSV 或 Excel(.xlsx/.xls)
        '''
        import pandas as pd

        if file_path.endswith('.csv'):
            self.data = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            self.data = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")
        result_text= f"加载成功：{self.data.shape[0]} 行 {self.data.shape[1]} 列\n列名：{', '.join(map(str, self.data.columns))}"
        self.report_sections.append(f"## 数据加载\n\n文件：{file_path}\n{result_text}\n\n")

        return result_text

    @tool_action("overview", "查看数据概况：形状/列类型/缺失值/前几行")
    def overview(self)-> str:
        '''从类变量取 DataFrame → 返回形状 / 列类型 / 缺失值 / 前 3 行摘要'''
        if self.data is None:
            return "尚未加载数据，请先调用 load_data"
        result_text = f"形状：{self.data.shape}\n列类型：{dict(self.data.dtypes)}\n缺失值：{dict(self.data.isnull().sum())}\n前3行：{self.data.head(3).to_dict(orient='records')}"
        self.report_sections.append(f"## 数据概况\n\n{result_text}\n\n")
        return result_text

    def run(self, parameters):
        raise NotImplementedError("可展开工具请调用子工具")

    def get_parameters(self):
        return []

    @tool_action("clean_data", "清理数据：去重、处理缺失（数值填中位数，文本填未知）、类型转换等,返回清洗前后行数对比")
    def clean_data(self)-> str:
        '''清理数据：去重、处理缺失（数值填中位数，文本填未知）、类型转换等'''
        if self.data is None:
            return "尚未加载数据，请先调用 load_data"
        import pandas as pd
        # 去重
        shape_before = self.data.shape
        self.data.drop_duplicates(inplace=True)
        # 处理缺失值（pandas 3.0 CoW：必须用赋值式，不能用链式 inplace）
        for col in self.data.columns:
            if pd.api.types.is_numeric_dtype(self.data[col]):
                median = self.data[col].median()
                self.data[col] = self.data[col].fillna(median)
            else:
                if isinstance(self.data[col].dtype, pd.CategoricalDtype):
                    self.data[col] = self.data[col].cat.add_categories("未知").fillna("未知")
                else:
                    self.data[col] = self.data[col].fillna("未知")
        # 类型转换（尝试将对象列转换为类别型）
        for col in self.data.select_dtypes(include=['object']).columns:
            try:
                self.data[col] = self.data[col].astype('category')
            except Exception as e:
                print(f"转换列 {col} 时出错：{e}")
        result_text = f"清理完成：清理前 {shape_before[0]} 行，清理后 {self.data.shape[0]} 行，当前数据形状 {self.data.shape}"
        self.report_sections.append(f"## 数据清理\n\n{result_text}\n\n")
        return result_text



    @tool_action("statistics", "数据列describe统计+相关系数矩阵，返回文本摘要（相关性 Top 对）")
    def statistics(self)-> str:
        '''返回数据列的 describe 统计信息和相关系数矩阵'''
        if self.data is None:
            return "尚未加载数据，请先调用 load_data"
        # 1. 数值列的描述统计（只挑关键行，控制长度）
        desc = self.data.describe().round(2)
        text = [f"描述统计：{desc.to_string()}"]
        # 2. 相关性只保留 |r| > 0.3 的对
        corr = self.data.select_dtypes(include='number').corr()
        pairs = []
        cols = list(corr.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                v = corr.iloc[i, j]
                if abs(v) >= 0.3:
                    pairs.append(f"{cols[i]} ↔ {cols[j]}: {v:.2f}")
        text.append("【相关性显著的对】")
        text.extend(pairs if pairs else ["（无明显强相关）"])
        self.report_sections.append(f"## 相关性分析\n\n{'\n'.join(text)}\n\n")
        return "\n".join(text)



    @tool_action("group_by", "分组聚合(mean/sum/count)，返回分组结果文本")
    def group_by(self, group_cols: list, agg_col: str, agg_func: str)->str:
        '''按指定列分组并聚合

        Args:
            group_cols: 分组列列表
            agg_col: 聚合列
            agg_func: 聚合函数，支持 mean/sum/count
        '''
        if self.data is None:
            return "尚未加载数据，请先调用 load_data"
        if not all(col in self.data.columns for col in group_cols + [agg_col]):
            return "指定的列不存在于数据中"
        if agg_func not in ['mean', 'sum', 'count']:
            return "不支持的聚合函数，请使用 mean/sum/count"


        grouped = self.data.groupby(group_cols).agg({agg_col: agg_func}).reset_index()
        result_text = f"分组聚合结果：\n{grouped.to_string(index=False)}"
        self.report_sections.append(f"## 分组聚合\n\n{result_text}\n\n")
        return result_text

    @tool_action("visualize", "matplotlib 画图存 `outputs/` 目录,返回图表文件路径")
    def visualize(self, x_col: str, y_col: str, chart_type: str = 'line')-> str:
        '''可视化数据，支持 line/bar/pie（自动加中文标题、轴标签与图例）

        Args:
            x_col: x 轴列名
            y_col: y 轴列名
            chart_type: 图表类型，支持 line/bar/pie
        '''
        if self.data is None:
            return "尚未加载数据，请先调用 load_data"
        if x_col not in self.data.columns or y_col not in self.data.columns:
            return "指定的列不存在于数据中"
        if chart_type not in ['line', 'bar', 'pie']:
            return "不支持的图表类型，请使用 line/bar/pie"

        import matplotlib.pyplot as plt
        import os

        # 常见列名 → 中文（未知列名回退原英文名）
        COLUMN_ZH = {
            "age": "年龄", "country": "国家", "prior_programming_experience": "先备编程经验",
            "weeks_in_course": "课程周数", "hours_spent_learning_per_week": "每周学习小时数",
            "practice_problems_solved": "已解决练习题数", "projects_completed": "完成项目数",
            "tutorial_videos_watched": "观看教程视频数", "uses_kaggle": "使用Kaggle",
            "participates_in_discussion_forums": "参与讨论论坛", "debugging_sessions_per_week": "每周调试次数",
            "self_reported_confidence_python": "Python信心度", "final_exam_score": "期末成绩",
            "passed_exam": "是否通过考试", "student_id": "学生ID",
        }
        def zh(col: str) -> str:
            return COLUMN_ZH.get(col, col)

        # 确保 outputs 目录存在
        os.makedirs("outputs", exist_ok=True)
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        if chart_type == 'line':
            import pandas as _pd
            import numpy as np
            # 数值化并丢弃缺失，避免字符串/NaN 干扰
            s = _pd.to_numeric(self.data[x_col], errors='coerce')
            y = _pd.to_numeric(self.data[y_col], errors='coerce')
            df = _pd.DataFrame({x_col: s, y_col: y}).dropna()
            if df.empty:
                return "x/y 列无可用的数值数据"
            if df[x_col].nunique() > 20:
                # 连续数值 → 分 10 箱取均值，得到清晰趋势线（避免 500 个点来回折返）
                bins = np.linspace(df[x_col].min(), df[x_col].max(), 11)
                mid = [(bins[i] + bins[i + 1]) / 2 for i in range(10)]
                df['bin'] = _pd.cut(df[x_col], bins=bins, labels=mid, include_lowest=True)
                agg = df.groupby('bin', observed=True)[y_col].mean()
                plt.plot(agg.index.astype(float), agg.values, marker='o', markersize=4)
                plt.xticks(rotation=30)
            else:
                # 离散数值（如 0/1）→ 按值排序取均值
                agg = df.groupby(x_col)[y_col].mean().sort_index()
                plt.plot(agg.index.astype(float), agg.values, marker='o', markersize=4)
            plt.title(f"{zh(y_col)} 随 {zh(x_col)} 变化")
            plt.xlabel(zh(x_col))
            plt.ylabel(zh(y_col))
            plt.grid(True, alpha=0.3)
        elif chart_type == 'bar':
            x_vals = self.data[x_col].fillna("未知").astype(str)  # NaN 先填充再转 str（astype 对 NaN 保留 float）
            plt.bar(x_vals, self.data[y_col])
            plt.title(f"{zh(x_col)} 与 {zh(y_col)} 对比")
            plt.xlabel(zh(x_col))
            plt.ylabel(zh(y_col))
            plt.xticks(rotation=30)
        elif chart_type == 'pie':
            labels = self.data[x_col].fillna("未知").astype(str)
            sizes = self.data[y_col].fillna(0)  # NaN 兜底为 0，避免 Wedge 报错
            plt.pie(sizes, labels=labels, autopct='%1.1f%%')
            plt.title(f"{zh(y_col)} 分布")
        else:
            return "不支持的图表类型，请使用 line/bar/pie"

        # 保存图表
        file_path = f"outputs/{x_col}_{y_col}_{chart_type}.png"
        plt.savefig(file_path, bbox_inches='tight')
        plt.close()
        self.report_sections.append(f"## 可视化\n\n图表：{file_path}\n\n")

        return file_path

    @tool_action("predict", "sklearn 建模 + 评估（R²/ 准确率）,返回模型性能指标")
    def predict(self, target_col: str, task: str)-> str:
        '''使用 sklearn 建模并评估模型性能

        Args:
            target_col: 目标列名
            task: 任务类型，支持 regression/classification
        '''
        if self.data is None:
            return "尚未加载数据，请先调用 load_data"
        if target_col not in self.data.columns:
            return "指定的目标列不存在于数据中"
        if task not in ['regression', 'classification']:
            return "不支持的任务类型，请使用 regression/classification"

        from sklearn.model_selection import train_test_split
        from sklearn.linear_model import LinearRegression, LogisticRegression
        from sklearn.metrics import r2_score, accuracy_score
        import pandas as pd

        # 准备数据（防目标泄漏：只剔除"实际存在"的标识符/代理列，适配任意数据集）
        exclude = {target_col}
        if "student_id" in self.data.columns:
            exclude.add("student_id")
        # 回归时再排除二值代理列（若存在）
        if task == "regression" and "passed_exam" in self.data.columns:
            exclude.add("passed_exam")
        X = self.data.drop(columns=list(exclude))

        y = self.data[target_col]

        # 简单处理非数值列（仅示例，实际应更复杂）
        X = pd.get_dummies(X, drop_first=True)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        if task == 'regression':
            model = LinearRegression()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            score = r2_score(y_test, y_pred)
            self.report_sections.append(f"## 模型预测\n\n模型：LinearRegression, R²: {score:.4f}\n\n")
            return f"模型：LinearRegression, R²: {score:.4f}"
        else:  # classification
            model = LogisticRegression(max_iter=1000)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            score = accuracy_score(y_test, y_pred)
            self.report_sections.append(f"## 模型预测\n\n模型：LogisticRegression, 准确率: {score:.4f}\n\n")
            return f"模型：LogisticRegression, 准确率: {score:.4f}"


    @tool_action("write_report",  "把前面所有步骤的文本汇总成 Markdown 存 outputs/report.md,返回报告文件路径")
    def write_report(self) -> str:
        '''将前面所有步骤的文本汇总成 Markdown 并保存到 outputs/report.md，返回报告文件路径'''
        # 确保 outputs 目录存在
        import os
        os.makedirs("outputs", exist_ok=True)
        report_path = "outputs/report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            if self.data is not None:
                f.write(f"# 数据分析报告\n\n")
                f.write(f"\n\n".join(self.report_sections))
            else:
                f.write("尚未加载数据。\n")
        return report_path
