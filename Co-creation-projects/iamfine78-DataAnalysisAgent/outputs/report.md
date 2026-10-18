# 数据分析报告

## 数据加载

文件：data/python_learning_exam_performance.csv
加载成功：500 行 15 列
列名：student_id, age, country, prior_programming_experience, weeks_in_course, hours_spent_learning_per_week, practice_problems_solved, projects_completed, tutorial_videos_watched, uses_kaggle, participates_in_discussion_forums, debugging_sessions_per_week, self_reported_confidence_python, final_exam_score, passed_exam



## 数据概况

形状：(500, 15)
列类型：{'student_id': dtype('int64'), 'age': dtype('int64'), 'country': <StringDtype(storage='python', na_value=nan)>, 'prior_programming_experience': <StringDtype(storage='python', na_value=nan)>, 'weeks_in_course': dtype('int64'), 'hours_spent_learning_per_week': dtype('float64'), 'practice_problems_solved': dtype('float64'), 'projects_completed': dtype('int64'), 'tutorial_videos_watched': dtype('float64'), 'uses_kaggle': dtype('int64'), 'participates_in_discussion_forums': dtype('int64'), 'debugging_sessions_per_week': dtype('int64'), 'self_reported_confidence_python': dtype('int64'), 'final_exam_score': dtype('float64'), 'passed_exam': dtype('float64')}
缺失值：{'student_id': np.int64(0), 'age': np.int64(0), 'country': np.int64(0), 'prior_programming_experience': np.int64(191), 'weeks_in_course': np.int64(0), 'hours_spent_learning_per_week': np.int64(1), 'practice_problems_solved': np.int64(2), 'projects_completed': np.int64(0), 'tutorial_videos_watched': np.int64(1), 'uses_kaggle': np.int64(0), 'participates_in_discussion_forums': np.int64(0), 'debugging_sessions_per_week': np.int64(0), 'self_reported_confidence_python': np.int64(0), 'final_exam_score': np.int64(1), 'passed_exam': np.int64(1)}
前3行：[{'student_id': 1, 'age': 54, 'country': 'Pakistan', 'prior_programming_experience': 'Beginner', 'weeks_in_course': 12, 'hours_spent_learning_per_week': 12.2, 'practice_problems_solved': 60.0, 'projects_completed': 1, 'tutorial_videos_watched': 24.0, 'uses_kaggle': 0, 'participates_in_discussion_forums': 1, 'debugging_sessions_per_week': 4, 'self_reported_confidence_python': 10, 'final_exam_score': 53.8, 'passed_exam': 0.0}, {'student_id': 2, 'age': 44, 'country': 'Nigeria', 'prior_programming_experience': nan, 'weeks_in_course': 15, 'hours_spent_learning_per_week': 14.2, 'practice_problems_solved': 52.0, 'projects_completed': 1, 'tutorial_videos_watched': 32.0, 'uses_kaggle': 0, 'participates_in_discussion_forums': 0, 'debugging_sessions_per_week': 5, 'self_reported_confidence_python': 7, 'final_exam_score': 31.9, 'passed_exam': 0.0}, {'student_id': 3, 'age': 30, 'country': 'India', 'prior_programming_experience': 'Intermediate', 'weeks_in_course': 5, 'hours_spent_learning_per_week': 7.7, 'practice_problems_solved': 71.0, 'projects_completed': 1, 'tutorial_videos_watched': 43.0, 'uses_kaggle': 0, 'participates_in_discussion_forums': 0, 'debugging_sessions_per_week': 6, 'self_reported_confidence_python': 3, 'final_exam_score': 59.4, 'passed_exam': 0.0}]



## 数据清理

清理完成：清理前 500 行，清理后 495 行，当前数据形状 (495, 15)



## 相关性分析

描述统计：       student_id     age  weeks_in_course  hours_spent_learning_per_week  practice_problems_solved  projects_completed  tutorial_videos_watched  uses_kaggle  participates_in_discussion_forums  debugging_sessions_per_week  self_reported_confidence_python  final_exam_score  passed_exam
count      495.00  495.00           495.00                         495.00                    495.00              495.00                   495.00       495.00                             495.00                       495.00                           495.00            495.00       495.00
mean       250.06   36.01             8.04                           7.10                     59.98                1.97                    40.30         0.40                               0.47                         5.00                             5.66             42.67         0.18
std        144.24   11.37             4.30                           3.13                      7.86                1.48                     6.37         0.49                               0.50                         2.13                             2.84             17.82         0.38
min          1.00   16.00             1.00                         -11.00                     39.00               -1.00                    24.00         0.00                               0.00                         0.00                             1.00              0.00         0.00
25%        126.50   26.50             4.00                           5.00                     54.00                1.00                    36.00         0.00                               0.00                         3.50                             3.00             29.60         0.00
50%        250.00   38.00             8.00                           7.00                     60.00                2.00                    40.00         0.00                               0.00                         5.00                             6.00             42.50         0.00
75%        374.50   46.00            12.00                           9.20                     65.00                3.00                    45.00         1.00                               1.00                         6.00                             8.00             55.30         0.00
max        499.00   54.00            15.00                          15.60                     85.00                8.00                    60.00         1.00                               1.00                        14.00                            10.00             92.80         1.00
【相关性显著的对】
hours_spent_learning_per_week ↔ final_exam_score: 0.41
projects_completed ↔ final_exam_score: 0.37
final_exam_score ↔ passed_exam: 0.69



## 分组聚合

分组聚合结果：
prior_programming_experience  final_exam_score
                    Advanced         64.948571
                    Beginner         42.789506
                Intermediate         57.305505
                          未知         29.993122



## 分组聚合

分组聚合结果：
 uses_kaggle  final_exam_score
           0         41.036271
           1         45.072000



## 分组聚合

分组聚合结果：
 participates_in_discussion_forums  final_exam_score
                                 0         42.451154
                                 1         42.905532



## 可视化

图表：outputs/prior_programming_experience_final_exam_score_bar.png



## 可视化

图表：outputs/hours_spent_learning_per_week_final_exam_score_line.png



## 可视化

图表：outputs/projects_completed_final_exam_score_line.png



## 可视化

图表：outputs/uses_kaggle_final_exam_score_bar.png



## 模型预测

模型：LinearRegression, R²: 0.7288

