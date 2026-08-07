"""
数据库查询工具集
"""
import oracledb
from typing import Dict, Any
from config import DatabaseConfig
from hello_agents import HelloAgentsLLM


class OracleQueryTool:
    """Oracle数据库查询工具"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        
    def connect(self) -> bool:
        """连接到Oracle数据库"""
        try:
            self.connection = oracledb.connect(
                user=self.config.username,
                password=self.config.password,
                host=self.config.host,
                port=self.config.port,
                service_name=self.config.service_name
            )
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, sql: str) -> Dict[str, Any]:
        """执行SQL查询并返回结果"""
        if not self.connection:
            if not self.connect():
                return {"success": False, "error": "无法连接到数据库"}
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            cursor.close()
            
            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "sql": sql
            }
        except Exception as e:
            return {"success": False, "error": str(e), "sql": sql}
    
    def get_schema_info(self) -> str:
        """获取数据库表结构信息"""
        if not self.connection:
            if not self.connect():
                return "无法连接到数据库"
        
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM user_tables 
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_info = []
            for table in tables:
                cursor.execute(f"""
                    SELECT column_name, data_type, nullable
                    FROM user_tab_columns
                    WHERE table_name = UPPER('{table}')
                    ORDER BY column_id
                """)
                columns = cursor.fetchall()
                
                col_desc = ", ".join([
                    f"{col[0]} ({col[1]})" 
                    for col in columns
                ])
                schema_info.append(f"表 {table}: {col_desc}")
            
            cursor.close()
            return "\n".join(schema_info)
        except Exception as e:
            return f"获取表结构失败: {e}"


class SQLGeneratorTool:
    """SQL生成工具 - 使用LLM将自然语言转换为SQL"""
    
    def __init__(self, llm: HelloAgentsLLM):
        self.llm = llm
        self.system_prompt = """你是一个专业的SQL查询生成助手。你的任务是将用户的自然语言查询转换为准确的Oracle SQL语句。

# 规则:
1. 只返回SQL语句，不要包含任何解释或额外文字
2. 使用Oracle SQL语法
3. 表名和字段名使用大写
4. 日期格式使用 'YYYY-MM-DD'
5. 字符串使用单引号
6. 确保SQL语句安全，避免SQL注入

# 数据库表结构:
{schema_info}

# 示例:
用户输入: 查询所有员工信息
输出: SELECT * FROM EMPLOYEES

用户输入: 查询工资大于5000的员工
输出: SELECT * FROM EMPLOYEES WHERE SALARY > 5000

现在，请根据用户的自然语言输入生成对应的SQL语句。
"""
    
    def generate_sql(self, natural_query: str, schema_info: str) -> str:
        """生成SQL语句"""
        prompt = self.system_prompt.format(schema_info=schema_info)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": natural_query}
        ]
        
        response = self.llm.invoke(messages)
        
        sql = response.strip()
        
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
    
    def validate_sql(self, sql: str) -> tuple[bool, str]:
        """验证SQL语句的基本语法"""
        sql_upper = sql.upper().strip()
        
        if not sql_upper.startswith(("SELECT", "WITH")):
            return False, "只允许SELECT查询语句"
        
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"不允许使用 {keyword} 语句"
        
        return True, "SQL语句验证通过"


def format_query_result(result: Dict[str, Any]) -> str:
    """格式化查询结果为表格"""
    if not result["success"]:
        return f"查询失败: {result['error']}"
    
    if result["row_count"] == 0:
        return "查询成功，但没有找到匹配的数据。"
    
    columns = result["columns"]
    rows = result["rows"]
    
    col_widths = []
    for i, col in enumerate(columns):
        max_width = max(len(str(col)), max(len(str(row[i])) for row in rows))
        col_widths.append(max_width + 2)
    
    separator = "+" + "+".join("-" * width for width in col_widths) + "+"
    
    header = "|" + "|".join(
        str(col).center(width) for col, width in zip(columns, col_widths)
    ) + "|"
    
    data_rows = []
    for row in rows:
        data_row = "|" + "|".join(
            str(cell).center(width) for cell, width in zip(row, col_widths)
        ) + "|"
        data_rows.append(data_row)
    
    table = [separator, header, separator] + data_rows + [separator]
    
    return "\n".join(table)