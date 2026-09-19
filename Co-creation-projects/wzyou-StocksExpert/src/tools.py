import akshare_one as ak
from typing import Literal
from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action
from typing import Dict, Any
from pandas import DataFrame


class AkShareTools(Tool):
    '''
    Tools for accessing various financial data via AkShare.

    历史数据	get_hist_data
    实时行情	get_realtime_data
    个股新闻	get_news_data
    财务数据	get_balance_sheet/get_income_statement/get_cash_flow
    期货数据	get_futures_hist_data/get_futures_realtime_data
    期权数据	get_options_chain/get_options_realtime/get_options_hist
    内部交易	get_inner_trade_data
    股票基本信息	get_basic_info
    财务指标	get_financial_metrics
    '''
    def __init__(self):
        super().__init__(
            name="akshare_tools",
            description="Tools for accessing various financial data via AkShare.",
            expandable=True
        )

    def get_parameters(self):
        return []

    def run(self, parameters: Dict[str, Any]):
        return ToolResponse.success(text="...", data={})

    
    @tool_action(name='get_hist_data', description="Get historical stock data")
    def _get_hist_data(
            self,
            symbol: str,
            interval: Literal['minute', 'hour', 'day', 'week', 'month', 'year'] = "day",
            interval_multiplier: int = 1,
            start_date: str = "1970-01-01",
            end_date: str = "2030-12-31",
            adjust: Literal['none', 'qfq', 'hfq'] = "none",
            source: Literal['eastmoney', 'eastmoney_direct', 'sina'] = "eastmoney_direct"
        ) -> DataFrame:
        '''
        Get historical stock data for a given symbol between start_date and end_date.

        Args:
            symbol (str): Stock symbol.
            interval (Literal['minute', 'hour', 'day', 'week', 'month', 'year']): Data interval.
            interval_multiplier (int): Multiplier for the interval.
            start_date (str): Start date for historical data.
            end_date (str): End date for historical data.
            adjust (Literal['none', 'qfq', 'hfq']): Adjustment type for the data.
            source (Literal['eastmoney', 'eastmoney_direct', 'sina']): Data source.


        Returns:
            DataFrame: Historical stock data for the given symbol between start_date and end_date.
        '''
        return ak.get_hist_data(
            symbol=symbol, 
            interval=interval, 
            interval_multiplier=interval_multiplier, 
            start_date=start_date, 
            end_date=end_date, 
            adjust=adjust, 
            source=source
            )

    @tool_action(name='get_realtime_data', description="Get real-time stock data")
    def _get_realtime_data(
            self,
            symbol: str,
            source: Literal['eastmoney', 'eastmoney_direct', 'xueqiu'] = "eastmoney"
        ) -> DataFrame:
        '''
        Get real-time stock data for a given symbol.

        Args:
            symbol (str): Stock symbol.
            source (Literal['eastmoney', 'eastmoney_direct', 'xueqiu']): Data source.

        Returns:
            DataFrame: Real-time stock data for the given symbol.
        '''
        return ak.get_realtime_data(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_news_data', description="Get news data")
    def _get_news_data(
            self,
            symbol: str,
            source: Literal['eastmoney'] = "eastmoney"
        ) -> DataFrame:
        '''
        Get news data for a given symbol.

        Args:
            symbol (str): Stock symbol.
            source (Literal['eastmoney's]): Data source.

        Returns:
            DataFrame: News data for the given symbol.
        '''
        return ak.get_news_data(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_balance_sheet', description="Get balance sheet data")
    def _get_balance_sheet(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get balance sheet data for a given symbol.

        Args:
            symbol (str): Stock symbol.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Balance sheet data for the given symbol.
        '''
        return ak.get_balance_sheet(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_income_statement', description="Get income statement data")
    def _get_income_statement(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get income statement data for a given symbol.

        Args:
            symbol (str): Stock symbol.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Income statement data for the given symbol.
        '''
        return ak.get_income_statement(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_cash_flow', description="Get cash flow data")
    def _get_cash_flow(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get cash flow data for a given symbol.

        Args:
            symbol (str): Stock symbol.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Cash flow data for the given symbol.
        '''
        return ak.get_cash_flow(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_futures_hist_data', description="Get futures historical data")
    def _get_futures_hist_data(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get futures historical data for a given symbol.

        Args:
            symbol (str): Futures symbol.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Futures historical data for the given symbol.
        '''
        return ak.get_futures_hist_data(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_futures_realtime_data', description="Get futures real-time data")
    def _get_futures_realtime_data(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get futures real-time data for a given symbol.

        Args:
            symbol (str): Futures symbol.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Futures real-time data for the given symbol.
        '''
        return ak.get_futures_realtime_data(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_options_chain', description="Get options chain data")
    def _get_options_chain(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get options chain data for a given symbol.

        Args:
            symbol (str): Underlying symbol for the options chain.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Options chain data for the given symbol.
        '''
        return ak.get_options_chain(
            underlying_symbol=symbol,
            source=source
        )

    @tool_action(name='get_options_realtime', description="Get options real-time data")
    def _get_options_realtime(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get options real-time data for a given symbol.

        Args:
            symbol (str): Underlying symbol for the options chain.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Options real-time data for the given symbol.
        '''
        return ak.get_options_realtime(
            underlying_symbol=symbol,
            source=source
        )

    @tool_action(name='get_options_hist', description="Get options historical data")
    def _get_options_hist(
            self,
            symbol: str,
            source: Literal['sina'] = "sina"
        ) -> DataFrame:
        '''
        Get options historical data for a given symbol.

        Args:
            symbol (str): Underlying symbol for the options chain.
            source (Literal['sina']): Data source.

        Returns:
            DataFrame: Options historical data for the given symbol.
        '''
        return ak.get_options_hist(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_inner_trade_data', description="Get inner trade data")
    def _get_inner_trade_data(
            self,
            symbol: str,
            source: Literal['xueqiu'] = "xueqiu"
        ) -> DataFrame:
        '''
        Get inner trade data for a given symbol.

        Args:
            symbol (str): Underlying symbol for the inner trade data.
            source (Literal['xueqiu']): Data source.

        Returns:
            DataFrame: Inner trade data for the given symbol.
        '''
        return ak.get_inner_trade_data(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_basic_info', description="Get basic stock information")
    def _get_basic_info(
            self,
            symbol: str,
            source: Literal['eastmoney'] = "eastmoney"
        ) -> DataFrame:
        '''
        Get basic stock information for a given symbol.

        Args:
            symbol (str): Underlying symbol for the stock.
            source (Literal['eastmoney']): Data source.

        Returns:
            DataFrame: Basic stock information for the given symbol.
        '''
        return ak.get_basic_info(
            symbol=symbol,
            source=source
        )

    @tool_action(name='get_financial_metrics', description="Get financial metrics")
    def _get_financial_metrics(
            self,
            symbol: str,
            source: Literal['eastmoney_direct'] = "eastmoney_direct"
        ) -> DataFrame:
        '''
        Get financial metrics for a given symbol.

        Args:
            symbol (str): Underlying symbol for the financial metrics.
            source (Literal['eastmoney_direct']): Data source.

        Returns:
            DataFrame: Financial metrics for the given symbol.
        '''
        return ak.get_financial_metrics(
            symbol=symbol,
            source=source
        )