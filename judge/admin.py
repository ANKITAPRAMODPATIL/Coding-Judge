from django.contrib import admin
from .models import (
    Problem, TestCase, Submission, UserProfile,
    Contest, Editorial, Discussion, Comment,
    LearningCategory, LearningItem, UserWorkspace, Reply, Vote
)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'created_at')
    search_fields = ('user__username', 'text')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'created_at')
    search_fields = ('user__username', 'text')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'vote_type', 'content_type', 'object_id')
    search_fields = ('user__username',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

admin.site.register(UserWorkspace)
admin.site.register(LearningCategory)
admin.site.register(LearningItem)
admin.site.register(Discussion)
admin.site.register(Editorial)

class TestcaseInline(admin.TabularInline):
    model = TestCase
    extra = 1

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('title', 'description', 'tags')
    inlines = [TestcaseInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'difficulty', 'tags')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user 
        super().save_model(request, obj, form, change)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem', 'language', 'status', 'submitted_at')
    list_filter = ('status', 'language', 'submitted_at')
    search_fields = ('user__username', 'problem__title')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'rating')
    search_fields = ('user__username',)

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('problem', 'input_data', 'expected_output')

@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time')
    filter_horizontal = ('problems',)
    