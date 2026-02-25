# data_analysis.py
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, f_oneway
from hello_agents import ToolRegistry

# 读取数据集
work_path = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(f"{work_path}/../data/shopping_behavior_updated.csv")

# 创建年龄段分组
def age_group(age):
    if age < 20:
        return 'Teen (<20)'
    elif age < 30:
        return '20s'
    elif age < 40:
        return '30s'
    elif age < 50:
        return '40s'
    elif age < 60:
        return '50s'
    else:
        return 'Senior (60+)'

df['Age Group'] = df['Age'].apply(age_group)

def analyze_gender_preferences(input: str) -> dict:
    """分析不同性别的购物偏好，返回可序列化的Python数据类型"""

    # 性别分布
    gender_counts_dict = df['Gender'].value_counts().to_dict()

    # 按性别统计平均消费金额
    gender_spending_series = df.groupby('Gender')['Purchase Amount (USD)'].mean()
    gender_spending_dict = gender_spending_series.to_dict()

    # 按性别统计最受欢迎的商品类别
    gender_category = df.groupby(['Gender', 'Category']).size().unstack(fill_value=0)
    gender_category_percent = gender_category.div(gender_category.sum(axis=1), axis=0)

    # 转换为嵌套字典
    gender_category_dict = gender_category_percent.to_dict('index')

    # 准备返回值 - 全部使用Python原生数据类型
    result = {
        'gender_distribution': gender_counts_dict,
        'average_spending_by_gender': gender_spending_dict,
        'category_preference_by_gender': gender_category_dict
    }

    # 可视化图表
    visualization_urls = []

    # 性别分布图
    plt.figure(figsize=(8, 5))
    plt.bar(gender_counts_dict.keys(), gender_counts_dict.values(), color=['blue', 'pink'])
    plt.title('Gender Distribution')
    plt.xlabel('Gender')
    plt.ylabel('Count')
    gender_distribution_path = 'figures/gender_distribution.png'
    plt.savefig(os.path.join(work_path, '../out', gender_distribution_path))
    plt.close()
    visualization_urls.append(gender_distribution_path)

    # 平均消费金额图
    plt.figure(figsize=(8, 5))
    plt.bar(gender_spending_dict.keys(), gender_spending_dict.values(), color=['blue', 'pink'])
    plt.title('Average Spending by Gender')
    plt.xlabel('Gender')
    plt.ylabel('Average Spending (USD)')
    average_spending_path = 'figures/average_spending_by_gender.png'
    plt.savefig(os.path.join(work_path, '../out', average_spending_path))
    plt.close()
    visualization_urls.append(average_spending_path)

    # 商品类别偏好图
    gender_category.plot(kind='bar', stacked=True, figsize=(10, 6))
    plt.title('Category Preference by Gender')
    plt.xlabel('Gender')
    plt.ylabel('Count')
    category_preference_path = 'figures/category_preference_by_gender.png'
    plt.savefig(os.path.join(work_path, '../out', category_preference_path))
    plt.close()
    visualization_urls.append(category_preference_path)

    result['visualization_url'] = visualization_urls

    return result


def analyze_age_preferences(input: str) -> dict:
    age_group_counts = df['Age Group'].value_counts().sort_index()
    age_group_counts_dict = age_group_counts.to_dict()

    # 按年龄段统计平均消费金额
    age_spending = df.groupby('Age Group')['Purchase Amount (USD)'].mean().sort_index()
    age_spending_dict = age_spending.to_dict()

    # 按年龄段统计最受欢迎的商品类别
    age_category = df.groupby(['Age Group', 'Category']).size().unstack(fill_value=0)
    age_category_percent = age_category.div(age_category.sum(axis=1), axis=0)
    age_category_percent = age_category_percent.to_dict('index')

    result = {
        'age_group_distribution': age_group_counts_dict,
        'average_spending_by_age_group': age_spending_dict,
        'category_preference_by_age_group': age_category_percent
    }

    # 可视化图表
    visualization_urls = []

    # 年龄段分布图
    plt.figure(figsize=(8, 5))
    plt.bar(age_group_counts_dict.keys(), age_group_counts_dict.values(), color='skyblue')
    plt.title('Age Group Distribution')
    plt.xlabel('Age Group')
    plt.ylabel('Count')
    age_distribution_path = 'figures/age_group_distribution.png'
    plt.savefig(os.path.join(work_path, '../out', age_distribution_path))
    plt.close()
    visualization_urls.append(age_distribution_path)

    # 平均消费金额图
    plt.figure(figsize=(8, 5))
    plt.bar(age_spending_dict.keys(), age_spending_dict.values(), color='lightgreen')
    plt.title('Average Spending by Age Group')
    plt.xlabel('Age Group')
    plt.ylabel('Average Spending (USD)')
    average_spending_path = 'figures/average_spending_by_age_group.png'
    plt.savefig(os.path.join(work_path, '../out', average_spending_path))
    plt.close()
    visualization_urls.append(average_spending_path)

    # 商品类别偏好图
    age_category.plot(kind='bar', stacked=True, figsize=(10, 6))
    plt.title('Category Preference by Age Group')
    plt.xlabel('Age Group')
    plt.ylabel('Count')
    category_preference_path = 'figures/category_preference_by_age_group.png'
    plt.savefig(os.path.join(work_path, '../out', category_preference_path))
    plt.close()
    visualization_urls.append(category_preference_path)

    result['visualization_url'] = visualization_urls  # 添加可视化图表路径到结果

    return result

def analyze_spending_differences(input: str) -> dict:
    # 按性别和年龄段分组统计
    gender_age_spending = df.groupby(['Gender', 'Age Group'])['Purchase Amount (USD)'].mean().unstack()
    gender_age_spending_dict = gender_age_spending.to_dict()

    # 按商品类别和年龄段分组统计
    category_age_spending = df.groupby(['Category', 'Age Group'])['Purchase Amount (USD)'].mean().unstack()
    category_age_spending_dict = category_age_spending.to_dict()

    result = {
        'spending_by_gender_and_age': gender_age_spending_dict,
        'spending_by_category_and_age': category_age_spending_dict
    }

    # 可视化图表
    visualization_urls = []

    # 性别和年龄段消费差异图
    plt.figure(figsize=(10, 6))
    gender_age_spending.plot(kind='bar', figsize=(10, 6))
    plt.title('Average Spending by Gender and Age Group')
    plt.xlabel('Age Group')
    plt.ylabel('Average Spending (USD)')
    plt.xticks(rotation=0)
    gender_age_spending_path = 'figures/average_spending_by_gender_and_age.png'
    plt.savefig(os.path.join(work_path, '../out', gender_age_spending_path))
    plt.close()
    visualization_urls.append(gender_age_spending_path)

    # 商品类别和年龄段消费差异图
    plt.figure(figsize=(10, 6))
    category_age_spending.plot(kind='bar', figsize=(10, 6))
    plt.title('Average Spending by Category and Age Group')
    plt.xlabel('Age Group')
    plt.ylabel('Average Spending (USD)')
    plt.xticks(rotation=0)
    category_age_spending_path = 'figures/average_spending_by_category_and_age.png'
    plt.savefig(os.path.join(work_path, '../out', category_age_spending_path))
    plt.close()
    visualization_urls.append(category_age_spending_path)

    result['visualization_url'] = visualization_urls  # 添加可视化图表路径到结果

    return result

def analyze_subscription_impact(input: str) -> dict:
    """
    分析订阅状态对消费的影响
    返回包含所有分析结果的字典
    """

    # 确保有Subscription Status列
    if 'Subscription Status' not in df.columns:
        return {"error": "数据中缺少Subscription Status列"}

    # 标准化订阅状态（处理大小写不一致）
    df['Subscription Status'] = df['Subscription Status'].str.strip().str.title()

    # 1. 基础统计：订阅用户与非订阅用户数量
    subscription_counts = df['Subscription Status'].value_counts().to_dict()

    # 2. 平均购买金额对比
    avg_purchase_by_subscription = df.groupby('Subscription Status')['Purchase Amount (USD)'].agg(['mean', 'std', 'count']).round(2)
    avg_purchase_dict = avg_purchase_by_subscription.to_dict('index')

    # 3. 之前购买次数对比
    prev_purchases_by_subscription = df.groupby('Subscription Status')['Previous Purchases'].agg(['mean', 'std', 'count']).round(2)
    prev_purchases_dict = prev_purchases_by_subscription.to_dict('index')

    # 4. 复购频率差异（如果Frequency of Purchases是数值类型）
    frequency_analysis = {}
    if 'Frequency of Purchases' in df.columns:
        # 创建频率映射（如果是分类数据）
        frequency_mapping = {
            'Weekly': 52,
            'Fortnightly': 26,
            'Bi-Weekly': 26,
            'Monthly': 12,
            'Quarterly': 4,
            'Every 3 Months': 4,
            'Annually': 1
        }

        # 转换为数值频率
        df['Purchase_Frequency_Numeric'] = df['Frequency of Purchases'].map(frequency_mapping)

        frequency_by_subscription = df.groupby('Subscription Status')['Purchase_Frequency_Numeric'].agg(['mean', 'std', 'count']).round(2)
        frequency_analysis = frequency_by_subscription.to_dict('index')

    # 5. 统计显著性检验
    significance_tests = {}

    # 分离订阅和非订阅用户数据
    subscribed = df[df['Subscription Status'] == 'Yes']
    not_subscribed = df[df['Subscription Status'] == 'No']

    # 6. 效应大小计算（Cohen's d）
    effect_sizes = {}

    if len(subscribed) > 0 and len(not_subscribed) > 0:
        # 购买金额的效应大小
        mean_diff_amount = subscribed['Purchase Amount (USD)'].mean() - not_subscribed['Purchase Amount (USD)'].mean()
        pooled_std_amount = np.sqrt(
            (subscribed['Purchase Amount (USD)'].std()**2 + not_subscribed['Purchase Amount (USD)'].std()**2) / 2
        )
        cohens_d_amount = mean_diff_amount / pooled_std_amount if pooled_std_amount > 0 else 0

        # 之前购买次数的效应大小
        mean_diff_prev = subscribed['Previous Purchases'].mean() - not_subscribed['Previous Purchases'].mean()
        pooled_std_prev = np.sqrt(
            (subscribed['Previous Purchases'].std()**2 + not_subscribed['Previous Purchases'].std()**2) / 2
        )
        cohens_d_prev = mean_diff_prev / pooled_std_prev if pooled_std_prev > 0 else 0

        effect_sizes = {
            'purchase_amount_cohens_d': round(cohens_d_amount, 3),
            'previous_purchases_cohens_d': round(cohens_d_prev, 3),
            'interpretation': {
                'small': 0.2,
                'medium': 0.5,
                'large': 0.8
            }
        }

    # 7. 按订阅状态分组的其他指标
    additional_metrics = {}

    # 购买金额的百分位数对比
    percentiles = [25, 50, 75, 90]
    for status in ['Yes', 'No']:
        status_data = df[df['Subscription Status'] == status]['Purchase Amount (USD)']
        percentile_dict = {}
        for p in percentiles:
            percentile_dict[f'p{p}'] = round(status_data.quantile(p/100), 2)
        additional_metrics[f'purchase_percentiles_{status.lower()}'] = percentile_dict

    # 8. 订阅用户的价值分析
    value_analysis = {}
    if 'Yes' in subscription_counts and 'No' in subscription_counts:
        total_revenue_subscribed = subscribed['Purchase Amount (USD)'].sum()
        total_revenue_not_subscribed = not_subscribed['Purchase Amount (USD)'].sum()

        avg_revenue_per_customer_subscribed = total_revenue_subscribed / len(subscribed)
        avg_revenue_per_customer_not_subscribed = total_revenue_not_subscribed / len(not_subscribed)

        value_analysis = {
            'total_revenue': {
                'subscribed': round(total_revenue_subscribed, 2),
                'not_subscribed': round(total_revenue_not_subscribed, 2),
                'ratio': round(total_revenue_subscribed / total_revenue_not_subscribed, 2) if total_revenue_not_subscribed > 0 else 'N/A'
            },
            'avg_revenue_per_customer': {
                'subscribed': round(avg_revenue_per_customer_subscribed, 2),
                'not_subscribed': round(avg_revenue_per_customer_not_subscribed, 2),
                'difference': round(avg_revenue_per_customer_subscribed - avg_revenue_per_customer_not_subscribed, 2)
            }
        }

    # 9. 类别购买差异分析（按订阅状态）
    category_analysis = {}
    category_by_subscription = df.groupby(['Subscription Status', 'Category']).size().unstack(fill_value=0)

    # 计算每个类别中订阅用户的占比
    for category in category_by_subscription.columns:
        total_category = category_by_subscription[category].sum()
        if total_category > 0:
            subscribed_pct = (category_by_subscription.loc['Yes', category] / total_category * 100) if 'Yes' in category_by_subscription.index else 0
            not_subscribed_pct = (category_by_subscription.loc['No', category] / total_category * 100) if 'No' in category_by_subscription.index else 0
            category_analysis[category] = {
                'subscribed_pct': round(subscribed_pct, 1),
                'not_subscribed_pct': round(not_subscribed_pct, 1),
                'subscribed_count': int(category_by_subscription.loc['Yes', category]) if 'Yes' in category_by_subscription.index else 0,
                'not_subscribed_count': int(category_by_subscription.loc['No', category]) if 'No' in category_by_subscription.index else 0
            }

    # 整合所有结果到一个字典
    results = {
        'basic_stats': {
            'subscription_counts': subscription_counts,
            'subscribed_percentage': round(subscription_counts.get('Yes', 0) / len(df) * 100, 1) if len(df) > 0 else 0
        },
        'purchase_amount_comparison': avg_purchase_dict,
        'previous_purchases_comparison': prev_purchases_dict,
        'purchase_frequency_analysis': frequency_analysis,
        'statistical_significance': significance_tests,
        'effect_sizes': effect_sizes,
        'percentile_analysis': additional_metrics,
        'customer_value_analysis': value_analysis,
        'category_preference_by_subscription': category_analysis,
        'summary': {
            'total_customers': len(df),
            'analysis_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_columns_used': ['Subscription Status', 'Purchase Amount (USD)', 'Previous Purchases', 'Frequency of Purchases', 'Category']
        }
    }

    # 可视化图表
    visualization_urls = []

    # 订阅用户与非订阅用户的平均购买金额对比图
    plt.figure(figsize=(8, 5))
    avg_purchase_by_subscription['mean'].plot(kind='bar', color=['blue', 'orange'])
    plt.title('Average Purchase Amount by Subscription Status')
    plt.xlabel('Subscription Status')
    plt.ylabel('Average Purchase Amount (USD)')
    purchase_amount_path = 'figures/average_purchase_by_subscription.png'
    plt.savefig(os.path.join(work_path, '../out', purchase_amount_path))
    plt.close()
    visualization_urls.append(purchase_amount_path)

    # 订阅用户与非订阅用户的之前购买次数对比图
    plt.figure(figsize=(8, 5))
    prev_purchases_by_subscription['mean'].plot(kind='bar', color=['blue', 'orange'])
    plt.title('Average Previous Purchases by Subscription Status')
    plt.xlabel('Subscription Status')
    plt.ylabel('Average Previous Purchases')
    previous_purchases_path = 'figures/average_previous_purchases_by_subscription.png'
    plt.savefig(os.path.join(work_path, '../out', previous_purchases_path))
    plt.close()
    visualization_urls.append(previous_purchases_path)

    results['visualization_url'] = visualization_urls  # 添加可视化图表路径到结果

    return results


def analyze_seasonal_preferences(input: str) -> dict:
    """
    季节性商品偏好分析
    按季节统计各商品类别的购买量及平均金额，找出各季节热销品类

    参数:

    返回:
        dict: 包含所有分析结果的字典
    """

    # 1. 数据预处理和验证
    required_columns = ['Season', 'Category', 'Purchase Amount (USD)']
    for col in required_columns:
        if col not in df.columns:
            return {"error": f"数据中缺少必要的列: {col}"}

    # 标准化季节名称
    season_mapping = {
        'spring': 'Spring',
        'summer': 'Summer',
        'fall': 'Fall',
        'winter': 'Winter',
        'Spring': 'Spring',
        'Summer': 'Summer',
        'Fall': 'Fall',
        'Winter': 'Winter'
    }

    df['Season'] = df['Season'].astype(str).str.strip().str.lower().map(lambda x: season_mapping.get(x, x))

    # 只保留有效的季节
    valid_seasons = ['Spring', 'Summer', 'Fall', 'Winter']

    # 2. 基础统计：各季节购买量分布
    seasonal_counts = df['Season'].value_counts().to_dict()
    total_purchases = len(df)

    # 3. 按季节和类别统计购买量和平均金额
    seasonal_analysis = {}

    for season in valid_seasons:
        season_data = df[df['Season'] == season]

        # 该季节的总购买量
        season_total = len(season_data)

        # 按类别统计
        category_stats = season_data.groupby('Category').agg({
            'Purchase Amount (USD)': ['count', 'mean', 'sum', 'std']
        }).round(2)

        # 重命名列
        category_stats.columns = ['count', 'avg_amount', 'total_amount', 'std_amount']
        category_stats = category_stats.reset_index()

        # 转换为字典格式
        category_dict = {}
        for _, row in category_stats.iterrows():
            category = row['Category']
            category_dict[category] = {
                'count': int(row['count']),
                'percentage': round(row['count'] / season_total * 100, 1),
                'avg_amount': float(row['avg_amount']),
                'total_amount': float(row['total_amount']),
                'std_amount': float(row['std_amount'])
            }

        # 找出该季节的热销品类（按购买量）
        top_categories_by_count = category_stats.nlargest(3, 'count')[['Category', 'count']].to_dict('records')
        top_categories_by_revenue = category_stats.nlargest(3, 'total_amount')[['Category', 'total_amount']].to_dict('records')

        # 季节特征分析
        season_summary = {
            'total_purchases': int(season_total),
            'percentage_of_total': round(season_total / total_purchases * 100, 1),
            'total_revenue': float(season_data['Purchase Amount (USD)'].sum()),
            'avg_transaction_value': float(season_data['Purchase Amount (USD)'].mean()),
            'top_categories_by_count': top_categories_by_count,
            'top_categories_by_revenue': top_categories_by_revenue,
            'category_details': category_dict
        }

        seasonal_analysis[season] = season_summary

    # 4. 季节性趋势分析（跨季节对比）
    seasonal_trends = {}

    # 计算每个类别在不同季节的表现
    all_categories = df['Category'].unique()

    for category in all_categories:
        category_data = df[df['Category'] == category]

        category_season_stats = []
        for season in valid_seasons:
            season_cat_data = category_data[category_data['Season'] == season]
            if len(season_cat_data) > 0:
                stats = {
                    'season': season,
                    'count': len(season_cat_data),
                    'avg_amount': float(season_cat_data['Purchase Amount (USD)'].mean()),
                    'total_amount': float(season_cat_data['Purchase Amount (USD)'].sum()),
                    'percentage': round(len(season_cat_data) / len(category_data) * 100, 1)
                }
                category_season_stats.append(stats)

        # 找出该类别的最佳销售季节
        if category_season_stats:
            best_by_count = max(category_season_stats, key=lambda x: x['count'])
            best_by_revenue = max(category_season_stats, key=lambda x: x['total_amount'])

            seasonal_trends[category] = {
                'total_purchases': len(category_data),
                'seasonal_distribution': category_season_stats,
                'best_season_by_count': {
                    'season': best_by_count['season'],
                    'count': best_by_count['count'],
                    'percentage': best_by_count['percentage']
                },
                'best_season_by_revenue': {
                    'season': best_by_revenue['season'],
                    'total_amount': best_by_revenue['total_amount']
                },
                'seasonality_index': calculate_seasonality_index(category_season_stats)
            }

    # 5. 季节性热点分析（找出具有明显季节性的品类）
    highly_seasonal_categories = []

    for category, trend in seasonal_trends.items():
        distribution = trend['seasonal_distribution']
        if len(distribution) >= 2:  # 至少有两个季节的数据
            counts = [d['count'] for d in distribution]
            max_count = max(counts)
            min_count = min(counts)

            if min_count > 0:  # 避免除以零
                seasonality_ratio = max_count / min_count
                if seasonality_ratio >= 2.0:  # 季节性差异显著（最高季节是最低季节的2倍以上）
                    highly_seasonal_categories.append({
                        'category': category,
                        'seasonality_ratio': round(seasonality_ratio, 2),
                        'peak_season': trend['best_season_by_count']['season'],
                        'peak_count': trend['best_season_by_count']['count']
                    })

    # 按季节性比例排序
    highly_seasonal_categories.sort(key=lambda x: x['seasonality_ratio'], reverse=True)

    # 6. 跨季节对比：整体数据
    cross_season_comparison = {}

    # 按季节的整体表现
    seasonal_performance = []
    for season in valid_seasons:
        if season in seasonal_analysis:
            season_data = seasonal_analysis[season]
            seasonal_performance.append({
                'season': season,
                'total_purchases': season_data['total_purchases'],
                'total_revenue': season_data['total_revenue'],
                'avg_transaction_value': season_data['avg_transaction_value'],
                'purchase_density': round(season_data['total_purchases'] / len(df[df['Season'] == season].index.unique()) if len(df[df['Season'] == season]) > 0 else 0, 2)
            })

    # 找出最高和最低销售季节
    if seasonal_performance:
        peak_season = max(seasonal_performance, key=lambda x: x['total_revenue'])
        low_season = min(seasonal_performance, key=lambda x: x['total_revenue'])

        cross_season_comparison = {
            'seasonal_performance': seasonal_performance,
            'peak_season': {
                'season': peak_season['season'],
                'total_revenue': peak_season['total_revenue'],
                'reason': analyze_peak_season_reason(seasonal_analysis[peak_season['season']])
            },
            'low_season': {
                'season': low_season['season'],
                'total_revenue': low_season['total_revenue']
            },
            'revenue_variation': round((peak_season['total_revenue'] - low_season['total_revenue']) / low_season['total_revenue'] * 100, 1) if low_season['total_revenue'] > 0 else 0
        }

    # 7. 季节性营销建议
    marketing_recommendations = generate_seasonal_recommendations(seasonal_analysis, seasonal_trends, highly_seasonal_categories)

    # 8. 汇总结果
    results = {
        'basic_stats': {
            'total_purchases': int(total_purchases),
            'seasons_covered': valid_seasons,
            'purchases_by_season': seasonal_counts,
            'categories_analyzed': list(all_categories)
        },
        'seasonal_analysis': seasonal_analysis,
        'category_seasonal_trends': seasonal_trends,
        'highly_seasonal_categories': highly_seasonal_categories[:10],  # 只返回前10个
        'cross_season_comparison': cross_season_comparison,
        'marketing_recommendations': marketing_recommendations,
        'summary': {
            'peak_season': cross_season_comparison.get('peak_season', {}).get('season', 'Unknown'),
            'most_consistent_category': find_most_consistent_category(seasonal_trends),
            'most_seasonal_category': highly_seasonal_categories[0]['category'] if highly_seasonal_categories else 'None',
            'highest_avg_transaction_season': max(seasonal_performance, key=lambda x: x['avg_transaction_value'])['season'] if seasonal_performance else 'Unknown',
            'analysis_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }

    # 可视化图表并保存路径到 results
    visualization_urls = []
    figures_dir = os.path.join(work_path, '../out', 'figures')
    os.makedirs(figures_dir, exist_ok=True)

    try:
        # 1) 各季节购买量柱状图
        plt.figure(figsize=(8,5))
        seasons = valid_seasons
        counts = [seasonal_counts.get(s, 0) for s in seasons]
        plt.bar(seasons, counts, color=['#66c2a5','#fc8d62','#8da0cb','#e78ac3'])
        plt.title('Purchases by Season')
        plt.ylabel('Purchases')
        path1 = 'figures/purchases_by_season.png'
        plt.savefig(os.path.join(work_path, '../out', path1), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path1)
    except Exception:
        pass

    try:
        # 2) 季节性总体表现（总收入）柱状图
        if seasonal_performance:
            plt.figure(figsize=(8,5))
            seasons_perf = [s['season'] for s in seasonal_performance]
            revenues = [s['total_revenue'] for s in seasonal_performance]
            plt.bar(seasons_perf, revenues, color='steelblue')
            plt.title('Total Revenue by Season')
            plt.ylabel('Total Revenue (USD)')
            path2 = 'figures/total_revenue_by_season.png'
            plt.savefig(os.path.join(work_path, '../out', path2), bbox_inches='tight')
            plt.close()
            visualization_urls.append(path2)
    except Exception:
        pass

    try:
        # 3) 高季节性品类条形图（前10）
        if highly_seasonal_categories:
            top_seasonal = highly_seasonal_categories[:10]
            cats = [c['category'] for c in top_seasonal]
            ratios = [c['seasonality_ratio'] for c in top_seasonal]
            plt.figure(figsize=(10,5))
            plt.barh(cats[::-1], ratios[::-1], color='darkorange')
            plt.title('Top Highly Seasonal Categories (seasonality ratio)')
            plt.xlabel('Seasonality Ratio')
            path3 = 'figures/highly_seasonal_categories.png'
            plt.savefig(os.path.join(work_path, '../out', path3), bbox_inches='tight')
            plt.close()
            visualization_urls.append(path3)
    except Exception:
        pass

    try:
        # 4) 部分类目跨季节堆叠柱状图（取出现频率较高的前8类）
        sample_cats = list(seasonal_trends.keys())[:8]
        if sample_cats:
            matrix = {s: {season:0 for season in valid_seasons} for s in sample_cats}
            for cat in sample_cats:
                dist = seasonal_trends.get(cat, {}).get('seasonal_distribution', [])
                for d in dist:
                    season = d.get('season')
                    count = d.get('count', 0)
                    if season in valid_seasons:
                        matrix[cat][season] = count
            df_matrix = pd.DataFrame.from_dict(matrix, orient='index')[valid_seasons]
            plt.figure(figsize=(10,6))
            df_matrix.plot(kind='bar', stacked=True, figsize=(10,6), colormap='tab20')
            plt.title('Seasonal Distribution for Sample Categories')
            plt.xlabel('Category')
            plt.ylabel('Purchase Count')
            plt.xticks(rotation=45, ha='right')
            path4 = 'figures/sample_categories_seasonal_distribution.png'
            plt.savefig(os.path.join(work_path, '../out', path4), bbox_inches='tight')
            plt.close()
            visualization_urls.append(path4)
    except Exception:
        pass

    # 将图表路径加入结果字典（相对 out/ 下的路径列表）
    results['visualization_url'] = visualization_urls

    return results


def calculate_seasonality_index(seasonal_stats):
    """计算季节性指数"""
    if not seasonal_stats:
        return 0

    counts = [s['count'] for s in seasonal_stats]
    avg_count = sum(counts) / len(counts)

    if avg_count == 0:
        return 0

    # 计算变异系数作为季节性指数
    variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
    std_dev = variance ** 0.5
    seasonality_index = std_dev / avg_count if avg_count > 0 else 0

    return round(seasonality_index, 3)


def analyze_peak_season_reason(season_data):
    """分析高峰季节的原因"""
    top_categories = season_data['top_categories_by_count'][:2]
    reasons = []

    for cat in top_categories:
        category_name = cat['Category']
        category_details = season_data['category_details'].get(category_name, {})
        reasons.append(f"{category_name} ({cat['count']}次购买，占总数的{category_details.get('percentage', 0)}%)")

    return f"主要贡献品类: {', '.join(reasons)}"


def analyze_monthly_trends():
    """分析月度趋势（如果有月份数据）"""
    monthly_insights = {}

    # 尝试从现有列中提取月份信息
    month_col = None
    for col in df.columns:
        if col.lower() in ['month', 'purchase_month', 'order_month']:
            month_col = col
            break

    if month_col:
        monthly_stats = df.groupby(month_col).agg({
            'Purchase Amount (USD)': ['count', 'mean', 'sum']
        }).round(2)

        monthly_stats.columns = ['count', 'avg_amount', 'total_amount']
        monthly_stats = monthly_stats.reset_index()

        monthly_insights = monthly_stats.to_dict('records')

    return monthly_insights


def generate_seasonal_recommendations(seasonal_analysis, seasonal_trends, highly_seasonal_categories):
    """生成季节性营销建议"""
    recommendations = []

    # 1. 库存管理建议
    for season, data in seasonal_analysis.items():
        top_categories = data['top_categories_by_count'][:3]
        if top_categories:
            categories_str = ', '.join([cat['Category'] for cat in top_categories])
            recommendations.append({
                'season': season,
                'type': '库存管理',
                'recommendation': f"增加 {categories_str} 品类的库存",
                'reason': f"该季节最受欢迎的品类，占总购买的{sum(data['category_details'][cat['Category']]['percentage'] for cat in top_categories if cat['Category'] in data['category_details']):.1f}%"
            })

    # 2. 促销活动建议
    for item in highly_seasonal_categories[:3]:
        recommendations.append({
            'category': item['category'],
            'type': '促销活动',
            'recommendation': f"在{item['peak_season']}季节进行重点促销",
            'reason': f"该品类在{item['peak_season']}季节的销量是其他季节的{item['seasonality_ratio']:.1f}倍"
        })

    # 3. 定价策略建议
    for season, data in seasonal_analysis.items():
        if data['avg_transaction_value'] > 0:
            # 找出该季节高价值品类
            high_value_categories = []
            for category, details in data['category_details'].items():
                if details['avg_amount'] > data['avg_transaction_value'] * 1.2:  # 高于平均20%
                    high_value_categories.append(category)

            if high_value_categories:
                recommendations.append({
                    'season': season,
                    'type': '定价策略',
                    'recommendation': f"对{', '.join(high_value_categories[:3])}品类进行溢价定价",
                    'reason': f"这些品类在该季节的平均交易价值较高 (${data['avg_transaction_value']:.2f}+)"
                })

    return recommendations


def find_most_consistent_category(seasonal_trends):
    """找出最稳定的品类（季节性差异最小）"""
    if not seasonal_trends:
        return "None"

    most_consistent = None
    min_seasonality = float('inf')

    for category, trend in seasonal_trends.items():
        seasonality = trend.get('seasonality_index', 1.0)
        if seasonality < min_seasonality:
            min_seasonality = seasonality
            most_consistent = category

    return most_consistent


def analyze_review_rating_impact(input: str) -> dict:
    """
    评论评分与消费关联分析

    参数:

    返回:
        dict: 包含最重要分析结果的字典
    """

    # 1. 数据预处理和验证
    required_columns = ['Review Rating', 'Purchase Amount (USD)', 'Previous Purchases']
    for col in required_columns:
        if col not in df.columns:
            return {"error": f"数据中缺少必要的列: {col}"}

    # 数据清洗
    df_clean = df.copy()
    df_clean['Review Rating'] = pd.to_numeric(df_clean['Review Rating'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Review Rating'])
    df_clean = df_clean[(df_clean['Review Rating'] >= 1) & (df_clean['Review Rating'] <= 5)]

    if len(df_clean) == 0:
        return {"error": "清洗后无有效数据"}

    # 2. 核心结果：评分组对比分析
    # 创建简化的评分区间
    def create_simple_rating_groups(rating):
        if rating >= 4.0:
            return 'High (4.0-5.0)'
        elif rating >= 3.0:
            return 'Medium (3.0-3.99)'
        else:
            return 'Low (1.0-2.99)'

    df_clean['Rating Group'] = df_clean['Review Rating'].apply(create_simple_rating_groups)

    # 评分组分析
    rating_group_analysis = {}
    for group in ['High (4.0-5.0)', 'Medium (3.0-3.99)', 'Low (1.0-2.99)']:
        if group in df_clean['Rating Group'].unique():
            group_data = df_clean[df_clean['Rating Group'] == group]
            rating_group_analysis[group] = {
                'customer_count': int(len(group_data)),
                'percentage': round(len(group_data) / len(df_clean) * 100, 1),
                'avg_purchase_amount': round(float(group_data['Purchase Amount (USD)'].mean()), 2),
                'avg_previous_purchases': round(float(group_data['Previous Purchases'].mean()), 1),
                'total_revenue': round(float(group_data['Purchase Amount (USD)'].sum()), 2)
            }

    # 3. 核心结果：相关性分析
    correlation_results = {}
    if len(df_clean) >= 10:
        try:
            # 评分与购买金额的相关性
            corr_amount, p_value_amount = pearsonr(
                df_clean['Review Rating'],
                df_clean['Purchase Amount (USD)']
            )

            # 评分与之前购买次数的相关性
            corr_prev, p_value_prev = pearsonr(
                df_clean['Review Rating'],
                df_clean['Previous Purchases']
            )

            correlation_results = {
                'rating_vs_purchase_amount': {
                    'correlation': round(corr_amount, 3),
                    'p_value': round(p_value_amount, 4),
                    'significant': p_value_amount < 0.05,
                    'strength': '强' if abs(corr_amount) >= 0.5 else '中' if abs(corr_amount) >= 0.3 else '弱'
                },
                'rating_vs_previous_purchases': {
                    'correlation': round(corr_prev, 3),
                    'p_value': round(p_value_prev, 4),
                    'significant': p_value_prev < 0.05
                }
            }
        except Exception:
            correlation_results = {'error': '相关性计算失败'}

    # 4. 核心结果：关键指标对比
    # 找出最高和最低评分组的差异
    key_comparisons = {}
    if len(rating_group_analysis) >= 2:
        high_group = rating_group_analysis.get('High (4.0-5.0)', {})
        low_group = rating_group_analysis.get('Low (1.0-2.99)', {})

        if high_group and low_group:
            amount_diff = high_group['avg_purchase_amount'] - low_group['avg_purchase_amount']
            prev_diff = high_group['avg_previous_purchases'] - low_group['avg_previous_purchases']

            key_comparisons = {
                'high_vs_low_rating': {
                    'purchase_amount_difference': round(amount_diff, 2),
                    'purchase_amount_percentage_diff': round(amount_diff / low_group['avg_purchase_amount'] * 100, 1) if low_group['avg_purchase_amount'] > 0 else 0,
                    'previous_purchases_difference': round(prev_diff, 1),
                    'revenue_contribution_ratio': round(high_group['total_revenue'] / low_group['total_revenue'], 1) if low_group['total_revenue'] > 0 else 'N/A'
                }
            }

    # 5. 核心结果：业务洞察摘要
    insights = []

    # 评分分布洞察
    high_rating_percentage = rating_group_analysis.get('High (4.0-5.0)', {}).get('percentage', 0)
    if high_rating_percentage > 50:
        insights.append("超过一半的客户给出高评分(4.0+)，表明总体满意度较高")
    elif high_rating_percentage < 30:
        insights.append("高评分客户比例较低，需要关注服务质量提升")

    # 消费差异洞察
    if key_comparisons and 'high_vs_low_rating' in key_comparisons:
        diff_info = key_comparisons['high_vs_low_rating']
        insights.append(f"高评分客户比低评分客户平均多消费${diff_info['purchase_amount_difference']:.2f} ({diff_info['purchase_amount_percentage_diff']:.1f}%)")

    # 相关性洞察
    if correlation_results and 'rating_vs_purchase_amount' in correlation_results:
        corr_info = correlation_results['rating_vs_purchase_amount']
        if corr_info['significant']:
            direction = "正" if corr_info['correlation'] > 0 else "负"
            insights.append(f"评分与消费金额存在{direction}相关关系({corr_info['strength']}相关，r={corr_info['correlation']:.2f})")

    # 6. 整合最重要的结果
    results = {
        'overall_summary': {
            'total_customers': int(len(df_clean)),
            'avg_rating': round(float(df_clean['Review Rating'].mean()), 2),
            'avg_purchase_amount': round(float(df_clean['Purchase Amount (USD)'].mean()), 2),
            'avg_previous_purchases': round(float(df_clean['Previous Purchases'].mean()), 1)
        },
        'rating_distribution': {
            'high_rating_percentage': high_rating_percentage,
            'rating_groups_summary': {
                group: {
                    'customer_count': data['customer_count'],
                    'percentage': data['percentage']
                }
                for group, data in rating_group_analysis.items()
            }
        },
        'key_metrics_by_rating': {
            group: {
                'avg_purchase_amount': data['avg_purchase_amount'],
                'avg_previous_purchases': data['avg_previous_purchases'],
                'total_revenue': data['total_revenue']
            }
            for group, data in rating_group_analysis.items()
        },
        'correlation_analysis': correlation_results,
        'key_comparisons': key_comparisons,
        'top_insights': insights[:3] if insights else ["数据不足或无明显模式"],
        'analysis_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 可视化图表并保存路径到 results
    visualization_urls = []
    figures_dir = os.path.join(work_path, '../out', 'figures')
    os.makedirs(figures_dir, exist_ok=True)

    try:
        # 1) 评分分布柱状图（High/Med/Low）
        groups = ['High (4.0-5.0)', 'Medium (3.0-3.99)', 'Low (1.0-2.99)']
        counts = [rating_group_analysis.get(g, {}).get('customer_count', 0) for g in groups]
        plt.figure(figsize=(7,4))
        plt.bar(groups, counts, color=['#4CAF50','#FFD54F','#EF5350'])
        plt.title('Rating Group Distribution')
        plt.ylabel('Customer Count')
        path1 = 'figures/rating_group_distribution.png'
        plt.savefig(os.path.join(work_path, '../out', path1), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path1)
    except Exception:
        pass

    try:
        # 2) 各评分组平均消费金额柱状图
        avg_amounts = [rating_group_analysis.get(g, {}).get('avg_purchase_amount', 0) for g in groups]
        plt.figure(figsize=(7,4))
        plt.bar(groups, avg_amounts, color=['#2E7D32','#F9A825','#C62828'])
        plt.title('Average Purchase Amount by Rating Group')
        plt.ylabel('Average Purchase Amount (USD)')
        path2 = 'figures/avg_purchase_by_rating_group.png'
        plt.savefig(os.path.join(work_path, '../out', path2), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path2)
    except Exception:
        pass

    try:
        # 3) 评分 vs 购买金额 散点图（样本点）
        plt.figure(figsize=(7,5))
        plt.scatter(df_clean['Review Rating'], df_clean['Purchase Amount (USD)'], alpha=0.6, s=20)
        plt.xlabel('Review Rating')
        plt.ylabel('Purchase Amount (USD)')
        plt.title('Rating vs Purchase Amount')
        path3 = 'figures/rating_vs_purchase_scatter.png'
        plt.savefig(os.path.join(work_path, '../out', path3), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path3)
    except Exception:
        pass

    try:
        # 4) 各评分组总收入柱状图
        totals = [rating_group_analysis.get(g, {}).get('total_revenue', 0) for g in groups]
        plt.figure(figsize=(7,4))
        plt.bar(groups, totals, color=['#66BB6A','#FFCA28','#EF5350'])
        plt.title('Total Revenue by Rating Group')
        plt.ylabel('Total Revenue (USD)')
        path4 = 'figures/total_revenue_by_rating_group.png'
        plt.savefig(os.path.join(work_path, '../out', path4), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path4)
    except Exception:
        pass

    # 将图表路径加入结果字典（相对 out/ 路径列表）
    results['visualization_url'] = visualization_urls

    return results

def analyze_payment_method_impact(input: str) -> dict:
    """
    支付方式对购买金额的影响分析

    参数:

    返回:
        dict: 包含分析结果的字典
    """

    # 1. 数据验证
    required_columns = ['Payment Method', 'Purchase Amount (USD)']
    for col in required_columns:
        if col not in df.columns:
            return {"error": f"数据中缺少必要的列: {col}"}

    # 2. 数据清洗
    df_clean = df.copy()
    df_clean['Payment Method'] = df_clean['Payment Method'].astype(str).str.strip()

    # 过滤无效数据
    df_clean = df_clean[df_clean['Purchase Amount (USD)'] > 0]

    if len(df_clean) == 0:
        return {"error": "清洗后无有效数据"}

    # 3. 基础统计分析
    # 支付方式分布
    payment_counts = df_clean['Payment Method'].value_counts().to_dict()
    total_transactions = len(df_clean)

    # 按支付方式的统计
    payment_stats = {}
    for method, group in df_clean.groupby('Payment Method'):
        payment_stats[method] = {
            'transaction_count': int(len(group)),
            'percentage': round(len(group) / total_transactions * 100, 1),
            'total_amount': round(float(group['Purchase Amount (USD)'].sum()), 2),
            'avg_amount': round(float(group['Purchase Amount (USD)'].mean()), 2),
            'median_amount': round(float(group['Purchase Amount (USD)'].median()), 2),
            'std_amount': round(float(group['Purchase Amount (USD)'].std()), 2),
            'min_amount': round(float(group['Purchase Amount (USD)'].min()), 2),
            'max_amount': round(float(group['Purchase Amount (USD)'].max()), 2)
        }

    # 4. 关键对比：最高和最低平均金额
    avg_amounts = {method: stats['avg_amount'] for method, stats in payment_stats.items()}
    if avg_amounts:
        max_avg_method = max(avg_amounts, key=avg_amounts.get)
        min_avg_method = min(avg_amounts, key=avg_amounts.get)

        key_comparisons = {
            'highest_avg_payment': {
                'method': max_avg_method,
                'amount': avg_amounts[max_avg_method],
                'details': payment_stats[max_avg_method]
            },
            'lowest_avg_payment': {
                'method': min_avg_method,
                'amount': avg_amounts[min_avg_method],
                'details': payment_stats[min_avg_method]
            },
            'difference': {
                'amount_diff': round(avg_amounts[max_avg_method] - avg_amounts[min_avg_method], 2),
                'percentage_diff': round((avg_amounts[max_avg_method] - avg_amounts[min_avg_method]) / avg_amounts[min_avg_method] * 100, 1) if avg_amounts[min_avg_method] > 0 else 0
            }
        }
    else:
        key_comparisons = {}

    # 5. 统计分析：ANOVA检验
    anova_results = {}
    if len(payment_stats) >= 2:
        try:
            # 准备各组数据
            groups = []
            for method in payment_stats.keys():
                group_data = df_clean[df_clean['Payment Method'] == method]['Purchase Amount (USD)'].values
                if len(group_data) >= 2:  # 至少2个样本
                    groups.append(group_data)

            if len(groups) >= 2:
                # 进行ANOVA检验
                f_stat, p_value = f_oneway(*groups)

                anova_results = {
                    'f_statistic': round(f_stat, 4),
                    'p_value': round(p_value, 6),
                    'significant': p_value < 0.05,
                    'interpretation': '不同支付方式间的购买金额存在显著差异' if p_value < 0.05 else '不同支付方式间的购买金额无显著差异'
                }
        except Exception as e:
            anova_results = {'error': f'ANOVA检验失败: {str(e)}'}

    # 6. 市场份额与金额贡献对比
    contribution_analysis = {}
    for method, stats in payment_stats.items():
        contribution_analysis[method] = {
            'transaction_share': stats['percentage'],
            'revenue_share': round(stats['total_amount'] / df_clean['Purchase Amount (USD)'].sum() * 100, 1),
            'avg_transaction_value': stats['avg_amount']
        }

    # 7. 业务洞察
    insights = []

    # 支付方式偏好洞察
    max_transactions = max(payment_counts.values())
    most_popular = [m for m, c in payment_counts.items() if c == max_transactions][0]
    insights.append(f"最常用的支付方式: {most_popular} ({payment_counts[most_popular]}笔交易)")

    # 金额差异洞察
    if key_comparisons:
        diff = key_comparisons['difference']
        insights.append(f"{key_comparisons['highest_avg_payment']['method']}的平均交易额比{key_comparisons['lowest_avg_payment']['method']}高{diff['percentage_diff']:.1f}%")

    # 统计显著性洞察
    if anova_results and 'significant' in anova_results:
        if anova_results['significant']:
            insights.append("不同支付方式间的消费金额存在统计显著差异")
        else:
            insights.append("不同支付方式间的消费金额无显著差异")

    # 高价值支付方式识别
    for method, contrib in contribution_analysis.items():
        if contrib['revenue_share'] > contrib['transaction_share'] + 10:  # 收入占比明显高于交易占比
            insights.append(f"{method}是高价值支付方式：贡献{contrib['revenue_share']}%的收入，但只占{contrib['transaction_share']}%的交易")

    # 8. 整合结果
    results = {
        'overall_summary': {
            'total_transactions': total_transactions,
            'total_revenue': round(float(df_clean['Purchase Amount (USD)'].sum()), 2),
            'avg_transaction_value': round(float(df_clean['Purchase Amount (USD)'].mean()), 2),
            'unique_payment_methods': len(payment_stats)
        },
        'payment_method_distribution': {
            'transaction_counts': payment_counts,
            'percentage_breakdown': {method: stats['percentage'] for method, stats in payment_stats.items()}
        },
        'performance_by_payment_method': payment_stats,
        'contribution_analysis': contribution_analysis,
        'key_comparisons': key_comparisons,
        'statistical_analysis': anova_results,
        'business_insights': insights[:5]
    }

    # 可视化图表并保存路径到 results
    visualization_urls = []
    figures_dir = os.path.join(work_path, '../out', 'figures')
    os.makedirs(figures_dir, exist_ok=True)

    try:
        # 1) 支付方式交易次数柱状图
        plt.figure(figsize=(8,5))
        methods = list(payment_counts.keys())
        counts = [payment_counts[m] for m in methods]
        plt.bar(methods, counts, color='skyblue')
        plt.title('Transaction Counts by Payment Method')
        plt.xlabel('Payment Method')
        plt.ylabel('Transaction Count')
        plt.xticks(rotation=45, ha='right')
        path_a = 'figures/payment_method_transaction_counts.png'
        plt.savefig(os.path.join(work_path, '../out', path_a), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path_a)
    except Exception:
        pass

    try:
        # 2) 支付方式占比饼图
        plt.figure(figsize=(6,6))
        series_counts = pd.Series(payment_counts)
        series_counts = series_counts.sort_values(ascending=False)
        series_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, pctdistance=0.75)
        plt.ylabel('')
        plt.title('Payment Method Share')
        path_b = 'figures/payment_method_share_pie.png'
        plt.savefig(os.path.join(work_path, '../out', path_b), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path_b)
    except Exception:
        pass

    try:
        # 3) 各支付方式平均交易额柱状图
        plt.figure(figsize=(8,5))
        methods_avg = list(avg_amounts.keys()) if 'avg_amounts' in locals() else list(payment_stats.keys())
        avg_vals = [payment_stats[m]['avg_amount'] if m in payment_stats else 0 for m in methods_avg]
        plt.bar(methods_avg, avg_vals, color='seagreen')
        plt.title('Average Transaction Value by Payment Method')
        plt.xlabel('Payment Method')
        plt.ylabel('Average Amount (USD)')
        plt.xticks(rotation=45, ha='right')
        path_c = 'figures/avg_transaction_value_by_payment_method.png'
        plt.savefig(os.path.join(work_path, '../out', path_c), bbox_inches='tight')
        plt.close()
        visualization_urls.append(path_c)
    except Exception:
        pass

    try:
        # 4) 支付方式金额分布箱线图（若样本量允许）
        grouped = []
        labels = []
        for method in payment_stats.keys():
            vals = df_clean[df_clean['Payment Method'] == method]['Purchase Amount (USD)'].dropna().values
            if len(vals) >= 3:
                grouped.append(vals)
                labels.append(method)
        if grouped:
            plt.figure(figsize=(10,6))
            plt.boxplot(grouped, tick_labels=labels, vert=True, patch_artist=True)
            plt.title('Purchase Amount Distribution by Payment Method')
            plt.ylabel('Purchase Amount (USD)')
            plt.xticks(rotation=45, ha='right')
            path_d = 'figures/purchase_amount_boxplot_by_payment_method.png'
            plt.savefig(os.path.join(work_path, '../out', path_d), bbox_inches='tight')
            plt.close()
            visualization_urls.append(path_d)
    except Exception:
        pass

    # 将图表路径加入结果字典（相对 out/ 下的路径列表）
    results['visualization_url'] = visualization_urls

    return results

def create_data_analysis_registry():
    """创建数据分析工具注册表"""
    tool_registry = ToolRegistry()

    # 注册数据分析工具
    tool_registry.register_function(
        name="Gender Preference Analysis",
        func=analyze_gender_preferences,
        description="分析不同性别的购物偏好，包括消费金额和商品类别偏好。"
    )

    tool_registry.register_function(
        name="Age Preference Analysis",
        func=analyze_age_preferences,
        description="分析不同年龄段的购物偏好，包括消费金额和商品类别偏好。"
    )

    tool_registry.register_function(
        name="Spending Differences Analysis",
        func=analyze_spending_differences,
        description="分析不同性别和年龄段在各商品类别上的消费差异。"
    )

    tool_registry.register_function(
        name="Subscription Impact Analysis",
        func=analyze_subscription_impact,
        description="分析订阅状态对用户购买行为和消费金额的影响。"
    )

    tool_registry.register_function(
        name="Seasonal Preference Analysis",
        func=analyze_seasonal_preferences,
        description="分析不同季节的商品购买偏好，找出各季节热销品类。"
    )

    tool_registry.register_function(
        name="Review Rating Impact Analysis",
        func=analyze_review_rating_impact,
        description="分析评论评分对用户购买金额和购买频率的影响。"
    )

    tool_registry.register_function(
        name="Payment Method Impact Analysis",
        func=analyze_payment_method_impact,
        description="分析不同支付方式对用户购买金额的影响。"
    )

    return tool_registry

if __name__ == "__main__":
    registry = create_data_analysis_registry()
    result = registry.execute_tool("Payment Method Impact Analysis", input_text=None)
    print(f"\n分析结果：{result}")
