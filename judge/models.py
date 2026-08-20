from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Problem(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20)
    tags = models.CharField(max_length=200)
    time_complexity = models.CharField(max_length=50, blank=True, null=True)
    space_complexity = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_verified = models.BooleanField(default=False)
    email_token = models.CharField(max_length=100, blank=True, null=True)
    company_tag = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.title


class TestCase(models.Model):
    problem = models.ForeignKey(
        Problem,
        related_name='testcases',
        on_delete=models.CASCADE
    )
    input_data = models.TextField()
    expected_output = models.TextField()
    is_hidden = models.BooleanField(default=False)

    def __str__(self):
        status = "Hidden" if self.is_hidden else "Sample"
        return f"{status} TestCase for {self.problem.title}"


class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=50, default="Pending", db_index=True)
    
    output = models.TextField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)  
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.status})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    score = models.IntegerField(default=0)
    rating = models.IntegerField(default=1200)
    streak_count = models.IntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    email_token = models.CharField(max_length=200, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    current_streak = models.IntegerField(default=0)
    last_submission_date = models.DateField(blank=True, null=True)
    streak = models.IntegerField(default=0)
    last_submission_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.user.username

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Contest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    problems = models.ManyToManyField(
        Problem,
        related_name='contests',
        blank=True
    )
    participants = models.ManyToManyField(
        User,
        related_name='participating_contests',
        blank=True
    )

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    @property
    def has_ended(self):
        return timezone.now() > self.end_time


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='🏆')

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class Editorial(models.Model):
    problem = models.OneToOneField(
        Problem,
        on_delete=models.CASCADE,
        related_name='editorial'
    )
    explanation = models.TextField()
    python_code = models.TextField(blank=True, null=True)
    cpp_code = models.TextField(blank=True, null=True)
    time_complexity = models.CharField(max_length=100, default='O(N)')
    space_complexity = models.CharField(max_length=100, default='O(1)')

    def __str__(self):
        return f"Editorial for {self.problem.title}"


class Discussion(models.Model):
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name='discussions'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.user.username}"


class LearningCategory(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.title


class LearningItem(models.Model):
    category = models.ForeignKey(
        LearningCategory,
        on_delete=models.CASCADE,
        related_name='items'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class UserWorkspace(models.Model):
    USER_CHOICES = (
        ('BOOKMARK', 'Bookmark'),
        ('FAVOURITE', 'Favorite Problem'),
        ('NOTE', 'Note'),
        ('RECENT', 'Recently Viewed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item_type = models.CharField(max_length=20, choices=USER_CHOICES)
    title = models.CharField(max_length=255)
    target_url = models.CharField(max_length=500, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.item_type}: {self.title}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.text[:30]}"


class Reply(models.Model):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.user.username}"


class Vote(models.Model):
    VOTE_CHOICES = (
        ('UP', 'Upvote'),
        ('DOWN', 'Downvote'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')

    def __str__(self):
        return f"{self.user.username} - {self.vote_type}"


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default="🏆") 

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.USER if hasattr(models, 'USER') else models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)  
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.action} at {self.timestamp}"

class Roadmap(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    slug = models.SlugField(unique=True)

    def __str__(self):
        self.title

class RoadmapStep(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=200)
    order = models.IntegerField(default=0)
    problems = models.ManyToManyField('Problem', blank=True)

    def __str__(self):
        return f"{self.roadmap.title} - {self.title}"        