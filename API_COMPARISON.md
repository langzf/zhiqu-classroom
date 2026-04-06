# API 前后端对比分析

## 后端 API 清单（按前缀分类）

### Auth `/api/v1/auth`
| Method | Path | OperationId |
|--------|------|------------|
| POST | /api/v1/auth/register | register |
| POST | /api/v1/auth/login | login |
| POST | /api/v1/auth/send-code | send_code |
| POST | /api/v1/auth/refresh | refresh_token |

### Admin-User `/api/v1/admin/users`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/admin/users | admin_list_users |
| POST | /api/v1/admin/users | admin_create_user |
| GET | /api/v1/admin/users/{user_id} | admin_get_user |
| PUT | /api/v1/admin/users/{user_id} | admin_update_user |
| DELETE | /api/v1/admin/users/{user_id} | admin_delete_user |
| PUT | /api/v1/admin/users/{user_id}/role | admin_set_role |
| PUT | /api/v1/admin/users/{user_id}/status | admin_set_status |

### Admin-Content `/api/v1/admin/content`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/admin/content/textbooks | admin_list_textbooks |
| POST | /api/v1/admin/content/textbooks | admin_create_textbook |
| GET | /api/v1/admin/content/textbooks/{textbook_id} | admin_get_textbook |
| PUT | /api/v1/admin/content/textbooks/{textbook_id} | admin_update_textbook |
| DELETE | /api/v1/admin/content/textbooks/{textbook_id} | admin_delete_textbook |
| POST | /api/v1/admin/content/textbooks/{textbook_id}/parse | admin_trigger_parse |
| GET | /api/v1/admin/content/chapters | admin_list_chapters |
| POST | /api/v1/admin/content/chapters | admin_create_chapter |
| GET | /api/v1/admin/content/chapters/{chapter_id} | admin_get_chapter |
| PUT | /api/v1/admin/content/chapters/{chapter_id} | admin_update_chapter |
| DELETE | /api/v1/admin/content/chapters/{chapter_id} | admin_delete_chapter |
| GET | /api/v1/admin/content/knowledge-points | admin_list_knowledge_points |
| POST | /api/v1/admin/content/knowledge-points | admin_create_knowledge_point |
| GET | /api/v1/admin/content/knowledge-points/{kp_id} | admin_get_knowledge_point |
| PUT | /api/v1/admin/content/knowledge-points/{kp_id} | admin_update_knowledge_point |
| DELETE | /api/v1/admin/content/knowledge-points/{kp_id} | admin_delete_knowledge_point |

### Admin-Learning `/api/v1/admin/learning`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/admin/learning/tasks | admin_list_tasks |
| POST | /api/v1/admin/learning/tasks | admin_create_task |
| GET | /api/v1/admin/learning/tasks/{task_id} | admin_get_task |
| PUT | /api/v1/admin/learning/tasks/{task_id} | admin_update_task |
| DELETE | /api/v1/admin/learning/tasks/{task_id} | admin_delete_task |
| GET | /api/v1/admin/learning/tasks/{task_id}/items | admin_list_task_items |
| POST | /api/v1/admin/learning/tasks/{task_id}/items | admin_add_task_item |
| GET | /api/v1/admin/learning/tasks/{task_id}/progress | admin_task_progress |

### App-User `/api/v1/app/user`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/app/user/me | get_my_profile |
| PUT | /api/v1/app/user/me | update_my_profile |

### App-Content `/api/v1/app/content`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/app/content/textbooks | list_textbooks |
| GET | /api/v1/app/content/textbooks/{textbook_id} | get_textbook_detail |
| GET | /api/v1/app/content/chapters/tree | get_chapter_tree |
| GET | /api/v1/app/content/knowledge-points/{kp_id} | get_knowledge_point |
| POST | /api/v1/app/content/knowledge-points/search | search_knowledge_points |

### App-Learning `/api/v1/app/learning`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/app/learning/tasks | my_tasks |
| GET | /api/v1/app/learning/tasks/{task_id} | get_task |
| POST | /api/v1/app/learning/tasks/{task_id}/start | start_task |
| POST | /api/v1/app/learning/tasks/{task_id}/submit | submit_task |
| GET | /api/v1/app/learning/learning-tasks | my_learning_tasks |
| POST | /api/v1/app/learning/learning-tasks | create_learning_task |
| GET | /api/v1/app/learning/mastery | my_mastery |
| POST | /api/v1/app/learning/study-sessions | create_study_session |
| PUT | /api/v1/app/learning/study-sessions/{session_id}/end | end_study_session |

### App-Tutor `/api/v1/app/tutor`
| Method | Path | OperationId |
|--------|------|------------|
| GET | /api/v1/app/tutor/conversations | list_conversations |
| POST | /api/v1/app/tutor/conversations | create_conversation |
| DELETE | /api/v1/app/tutor/conversations/{conv_id} | delete_conversation |
| GET | /api/v1/app/tutor/conversations/{conv_id}/messages | list_messages |
| POST | /api/v1/app/tutor/conversations/{conv_id}/messages | send_message |
| POST | /api/v1/app/tutor/feedback | add_feedback |
