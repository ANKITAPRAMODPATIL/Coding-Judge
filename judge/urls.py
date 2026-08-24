from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Core & Dashboard
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('workspace/', views.practice_workspace_view, name='practice_workspace'),

    # Problems & Editorials
    path('problems/', views.problem_list, name='problem_list'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('problem/<int:problem_id>/editorial/', views.editorial_view, name='problem_editorial'),
    path('problem/<int:problem_id>/discussions/', views.problem_discussions, name='problem_discussions'),
    path('problem/delete/<int:problem_id>/', views.delete_problem, name='delete_problem'),

    # Authentication & Profile
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/remove-avatar/', views.remove_avatar, name='remove_avatar'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
    path('submissions/', views.submission_history, name='submission_history'),
    path('verify/<str:token>/', views.verify_email, name='verify_email'),
    path('email-verification-sent/', TemplateView.as_view(template_name='judge/email_verification_sent.html'), name='email_verification_sent'),

    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='judge/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='judge/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='judge/password_reset_complete.html'), name='password_reset_complete'),

    # Code Execution & Submission API
    path('run-custom/', views.run_custom_code, name='run_custom_code'),
    path('submit-code/', views.submit_code_view, name='submit_code'),

    # Leaderboard & Contests
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('leaderboard/monthly/', views.monthly_leaderboard_view, name='monthly_leaderboard'),
    path('contests/', views.contest_list, name='contest_list'),
    path('contests/<int:contest_id>/', views.contest_detail, name='contest_detail'),
    path('contests/<int:contest_id>/join/', views.join_contest, name='join_contest'),
    path('contests/<int:contest_id>/leaderboard/', views.contest_leaderboard, name='contest_leaderboard'),
    path('certificate/', views.generate_certificate, name='generate_certificate'),

    # AI Tools & Discussions
    path('get-hint/<int:problem_id>/', views.get_ai_hint, name='get_ai_hint'),
    path('review-code/<int:problem_id>/', views.review_code, name='review_code'),
    path('ai-tools/', views.ai_tools_view, name='ai_tools'),
    path('discussion/<int:pk>/', views.discussion_detail, name='discussion_detail'),

    # Analytics & Progress (Fixed duplicate 'analytics/' path conflict)
    path('analytics/admin/', views.admin_analytics_dashboard, name='admin_analytics'),
    path('analytics/', views.analytics_view, name='analytics_dashboard'), 
    path('heatmap/', views.user_activity_heatmap, name='user_activity_heatmap'),
    path('topics-progress/', views.topic_wise_progress, name='topic_wise_progress'),
    path('company/<str:company_name>/', views.company_sheet, name='company_sheet'),

    # System & Extras
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('test-redis/', views.test_redis_view, name='test_redis'),
    path('roadmaps/', views.roadmap_list, name='roadmap_list'),
    path('roadmaps/<slug:slug>/', views.roadmap_detail, name='roadmap_detail'),
    path('debug-env-check/', views.debug_env),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)