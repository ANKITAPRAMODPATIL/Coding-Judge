import subprocess
import tempfile
import os
import sys
import io
import traceback
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from . import views
from django.core.mail import send_mail
from django.conf import settings
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Count, Q
from .models import UserProfile, Problem, Submission, Contest
from datetime import date
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Editorial
from .models import Discussion, Comment
from .models import Badge, UserBadge
from django.shortcuts import render
from .models import UserWorkspace
from django.contrib.contenttypes.models import ContentType
from .models import Comment, Reply, Vote
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from .tasks import execute_code_task
from django_ratelimit.decorators import ratelimit
from django.shortcuts import render
from .models import AuditLog
from core.utils import log_user_action
from django.core.cache import cache
from difflib import SequenceMatcher
from .models import Roadmap
from django.db.models import Count
from django.db.models.functions import TruncDate
from dotenv import load_dotenv

load_dotenv()
print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

def award_xp_and_level(user, difficulty, problem_title=None):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        xp_gained = 10  
        if difficulty and difficulty.lower() == 'medium':
            xp_gained = 20
        elif difficulty and difficulty.lower() == 'hard':
            xp_gained = 40
            
        profile.xp += xp_gained
        
        new_level = (profile.xp // 100) + 1
        if new_level > profile.level:
            profile.level = new_level
            
        if problem_title:
            profile.title = problem_title
            
        profile.save()
    except Exception as e:
        print("Error in award_xp_and_level:", e)

@csrf_exempt
def register_view(request):
  if request.method == 'POST':
    form = UserCreationForm(request.POST)
    if form.is_valid():
      user = form.save(commit=False)
      user.is_active = (
          False 
      )
      user.save()

      token = str(uuid.uuid4())
      UserProfile.objects.create(user=user, email_token=token)

      verify_link = request.build_absolute_uri(f'/verify/{token}/')

      subject = 'Verify your Email - Online Judge'
      message = (
          f'Hi {user.username},\n\nPlease click the link below to verify your'
          f' email:\n{verify_link}'
      )

      try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
      except Exception as e:
        
        print(f'Error sending verification email: {e}')

      return redirect('email_verification_sent')
  else:
    form = UserCreationForm()

  return render(request, 'judge/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('problem_list')
    else:
        form = AuthenticationForm()
    return render(request, 'judge/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')
@login_required(login_url='/login/')
def problem_list(request):
    query = request.GET.get('q', '')
    difficulty = request.GET.get('difficulty', '')
    problems = Problem.objects.all()
    if query:
        problems = problems.filter(Q(title__icontains=query) | Q(tags__icontains=query))
    if difficulty:
        problems = problems.filter(difficulty__iexact=difficulty)
    return render(request, 'judge/problem_list.html', {'problems': problems, 'query': query, 'selected_difficulty': difficulty})

@login_required(login_url='/login/')
def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)
    result = None
    user_code = ''
    selected_lang = 'python'
    custom_input = ''
    custom_output = ''
    test_results = []

    if request.method == 'POST':
        user_code = request.POST.get('code', '')
        selected_lang = request.POST.get('language', 'python')
        action = request.POST.get('action', 'submit')
        custom_input = request.POST.get('custom_input', '')

        if action == 'custom_run':
            custom_output = execute_code(user_code, selected_lang, custom_input)
            log_user_action(request.user, "Custom Run Code", request, details=f"Problem ID: {problem_id} ({selected_lang})")
            
        elif action == 'submit':
            
            cache_key = f"submission_cooldown_{request.user.id}"
            if cache.get(cache_key):
                result = 'Spam Protection: Please wait a few seconds before submitting again.'
            else:
                
                existing_subs = Submission.objects.filter(problem=problem)
                is_plagiarized = False
                for sub in existing_subs:
                    if SequenceMatcher(None, user_code, sub.code).ratio() > 0.9:  
                        is_plagiarized = True
                        break

                if is_plagiarized:
                    result = 'Plagiarism Detected: Your code is too similar to an existing submission.'
                else:
                   
                    cache.set(cache_key, True, timeout=10)

                    
                    test_cases = problem.testcases.all()
                    if not test_cases:
                        result = 'No Test Cases Found'
                    else:
                        all_passed = True
                        for i, tc in enumerate(test_cases, 1):
                            output = execute_code(user_code, selected_lang, tc.input_data or '')
                            passed = output.strip() == (tc.expected_output or '').strip()
                            if not passed:
                                all_passed = False
                            test_results.append({
                                'test_case': i,
                                'passed': passed,
                                'output': output.strip(),
                                'expected': tc.expected_output.strip()
                            })
                        result = 'Accepted' if all_passed else 'Wrong Answer'

                    
                    Submission.objects.create(
                        user=request.user, problem=problem, code=user_code, language=selected_lang, status=result, submitted_at=timezone.now()
                    )
                    
                    log_user_action(request.user, "Submitted Code", request, details=f"Problem ID: {problem_id} - Result: {result}")

                    
                    if result == 'Accepted':
                        profile, _ = UserProfile.objects.get_or_create(user=request.user)
                        profile.score += 10
                        profile.rating += 15
                        profile.save()
            
                        award_xp_and_level(request.user, problem.difficulty, problem.title)
                        update_user_streak(request.user)
                        check_and_award_badges(request.user)

    editorial = getattr(problem, 'editorial', None)
   
    context = {
        'problem': problem,
        'result': result,
        'user_code': user_code,
        'selected_lang': selected_lang,
        'custom_input': custom_input,
        'custom_output': custom_output,
        'test_results': test_results,
        'editorial': editorial,  
    }
    return render(request, 'judge/problem_detail.html', context)
def execute_code(code, language, input_data):
    try:
        if language == 'python':
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
                f.write(code.encode())
                f_name = f.name
            process = subprocess.run(['python', f_name], input=input_data.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            os.unlink(f_name)
            return process.stdout.decode() if process.returncode == 0 else process.stderr.decode()
        elif language == 'cpp':
            with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as f:
                f.write(code.encode())
                f_name = f.name
            exe_name = f_name[:-4]
            compile_process = subprocess.run(['g++', f_name, '-o', exe_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if compile_process.returncode != 0:
                os.unlink(f_name)
                return compile_process.stderr.decode()
            run_process = subprocess.run([exe_name], input=input_data.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            os.unlink(f_name)
            os.unlink(exe_name)
            return run_process.stdout.decode() if run_process.returncode == 0 else run_process.stderr.decode()
        elif language == 'javascript':
            with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as f:
                f.write(code.encode())
                f_name = f.name
            process = subprocess.run(['node', f_name], input=input_data.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            os.unlink(f_name)
            return process.stdout.decode() if process.returncode == 0 else process.stderr.decode()
    except Exception as e:
        return str(e)
    return "Unsupported Language"


@login_required(login_url='/login/') 
def leaderboard_view(request):
    profiles = UserProfile.objects.order_by('-score', '-rating')
    return render(request, 'judge/leaderboard.html', {'profiles': profiles})

@login_required(login_url='/login/')
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    solved_count = Submission.objects.filter(user=request.user, status='Accepted').values('problem').distinct().count()
    total_subs = Submission.objects.filter(user=request.user).count()
    
    context = {
        'profile': profile,
        'solved_count': solved_count,
        'total_subs': total_subs,
    }
    return render(request, 'judge/profile.html', context)

@login_required(login_url='/login/')
def submission_history(request):
    submissions = Submission.objects.filter(user=request.user).select_related('problem').order_by('-submitted_at')
    return render(request, 'judge/submission_history.html', {'submissions': submissions})


@csrf_exempt
@login_required(login_url='/login/')
def get_ai_hint(request, problem_id):
    try:
        problem = Problem.objects.get(id=problem_id)

        prompt = f"""
Give ONE short coding hint for this programming problem.

Rules:
- Maximum 2-3 sentences.
- Use simple English.
- Do not give the complete solution.
- Do not write code.
- Do not use headings like "Here is a hint".
- Do not use "Bonus Tip".
- Directly give the hint.

Title:
{problem.title}

Problem Description:
{problem.description}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        print("Gemini Status:", response.status_code)
        print("Gemini Response:", response.text)

        data = response.json()

        if response.status_code != 200:
            return JsonResponse({
                "error": data.get("error", {}).get(
                    "message",
                    "Gemini API request failed."
                )
            })

        candidates = data.get("candidates", [])

        if not candidates:
            return JsonResponse({
                "error": "Gemini did not return a hint."
            })

        hint = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not hint:
            return JsonResponse({
                "error": "Gemini returned an empty hint."
            })

        return JsonResponse({
            "hint": hint
        })

    except Problem.DoesNotExist:
        return JsonResponse({
            "error": "Problem not found."
        })

    except Exception as e:
        print("AI Hint Error:", str(e))
        return JsonResponse({
            "error": str(e)
        })
   
@csrf_exempt
@login_required(login_url='/login/')
def review_code(request, problem_id):
    try:
        problem = Problem.objects.get(id=problem_id)
        user_code = request.GET.get('code', '')

        if not user_code.strip():
            return JsonResponse({
                "error": "Please write some code before requesting a review."
            })

        prompt = f"""
Review the student's code for this programming problem.

Use exactly these three sections:

1. Bugs
2. Optimization
3. Edge Cases

Rules:
- Use simple and clear English.
- Be concise.
- Do not rewrite the complete solution.
- Do not add unnecessary introductions.
- Do not use markdown headings like ###.
- Mention "None" if there are no bugs.

Problem:
{problem.title}

Description:
{problem.description}

Student Code:
{user_code}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        print("Gemini Review Status:", response.status_code)
        print("Gemini Review Response:", response.text)

        data = response.json()

        if response.status_code != 200:
            return JsonResponse({
                "error": data.get("error", {}).get(
                    "message",
                    "Gemini API request failed."
                )
            })

        candidates = data.get("candidates", [])

        if not candidates:
            return JsonResponse({
                "error": "Gemini did not return a code review."
            })

        review = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not review:
            return JsonResponse({
                "error": "Gemini returned an empty review."
            })

        return JsonResponse({
            "review": review
        })

    except Problem.DoesNotExist:
        return JsonResponse({
            "error": "Problem not found."
        })

    except Exception as e:
        print("AI Review Error:", str(e))
        return JsonResponse({
            "error": str(e)
        })
   
def join_contest(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    contest.participants.add(request.user)
    return redirect('contest_detail', contest_id=contest.id)

@login_required(login_url='/login/')
def contest_detail(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    if request.user not in contest.participants.all():
        return redirect('contest_list')
    problems = contest.problems.all()
    return render(request, 'judge/contest_detail.html', {'contest': contest, 'problems': problems})

@login_required(login_url='/login/')
def contest_leaderboard(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    participants_data = []
    for user in contest.participants.all():
        solved_count = Submission.objects.filter(
            user=user,
            problem__in=contest.problems.all(),
            status='Accepted'
        ).values('problem').distinct().count()
        
        participants_data.append({
            'user': user,
            'score': solved_count
        })
    participants_data = sorted(participants_data, key=lambda x: x['score'], reverse=True)
    return render(request, 'judge/contest_leaderboard.html', {
        'contest': contest,
        'leaderboard': participants_data
    })   

@login_required(login_url='/login/')
def run_custom_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            custom_input = data.get('input', '')
            old_stdin = sys.stdin
            sys.stdin = io.StringIO(custom_input)
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()
            exec_globals = {}
            exec(code, exec_globals)
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            output = captured_output.getvalue()
            return JsonResponse({'success': True, 'output': output})
        except Exception as e:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            error_msg = traceback.format_exc()
            return JsonResponse({'success': False, 'output': error_msg})
    return JsonResponse({'success': False, 'output': 'Invalid request method.'})

def check_and_award_badges(user):
    solved_count = Submission.objects.filter(user=user, status='Accepted').values('problem').distinct().count()
    badge_conditions = [
        ('First Accepted', solved_count >= 1, '🎉', 'Solved your first problem successfully!'),
        ('10 Problems Solved', solved_count >= 10, '🏅', 'Solved 10 problems!'),
        ('50 Problems Solved', solved_count >= 50, '🔥', 'Solved 50 problems!'),
    ]
    for badge_name, condition, icon, desc in badge_conditions:
        if condition:
            badge, created = Badge.objects.get_or_create(
                name=badge_name, 
                defaults={'description': desc, 'icon': icon}
            )
            if not UserBadge.objects.filter(user=user, badge=badge).exists():
                UserBadge.objects.create(user=user, badge=badge)

@login_required(login_url='/login/')
def user_profile_view(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    today = date.today()
    if profile.last_active_date != today:
        if profile.last_active_date == today - timezone.timedelta(days=1):
            profile.streak_count += 1
        elif profile.last_active_date != today and profile.last_active_date is not None:
            profile.streak_count = 1
        elif profile.last_active_date is None:
            profile.streak_count = 1
        profile.last_active_date = today
        profile.save()

        if profile.streak_count >= 5:
            badge, _ = Badge.objects.get_or_create(
                name='Daily Streak', 
                defaults={'description': 'Maintained a 5-day coding streak!', 'icon': '⚡'}
            )
            if not UserBadge.objects.filter(user=user, badge=badge).exists():
                UserBadge.objects.create(user=user, badge=badge)

    user_badges = UserBadge.objects.filter(user=user).select_related('badge')
    solved_problems_count = Submission.objects.filter(user=user, status='Accepted').values('problem').distinct().count()

    return render(request, 'judge/profile.html', {
        'profile': profile,
        'user_badges': user_badges,
        'solved_problems_count': solved_problems_count
    })

@login_required(login_url='/login/')
def analytics_view(request):
    user = request.user
    user_submissions = Submission.objects.filter(user=user)
    solved_submissions = user_submissions.filter(status='Accepted').select_related('problem')
    difficulty_counts = {
        'Easy': solved_submissions.filter(problem__difficulty__iexact='Easy').values('problem').distinct().count(),
        'Medium': solved_submissions.filter(problem__difficulty__iexact='Medium').values('problem').distinct().count(),
        'Hard': solved_submissions.filter(problem__difficulty__iexact='Hard').values('problem').distinct().count(),
    }
    total_subs = user_submissions.count()
    accepted_subs = user_submissions.filter(status='Accepted').count()
    success_rate = round((accepted_subs / total_subs) * 100, 2) if total_subs > 0 else 0

    today = datetime.now().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    trend_labels = [d.strftime('%b %d') for d in dates]
    trend_counts = []
    for d in dates:
        count = user_submissions.filter(submitted_at__date=d).count()
        trend_counts.append(count)

    context = {
        'difficulty_counts': difficulty_counts,
        'total_subs': total_subs,
        'accepted_subs': accepted_subs,
        'success_rate': success_rate,
        'trend_labels': trend_labels,
        'trend_counts': trend_counts,
    }
    return render(request, 'judge/analytics.html', context)

@login_required(login_url='/login/')
def editorial_view(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    editorial = Editorial.objects.filter(problem=problem).first()
    return render(request, 'judge/editorial.html', {
        'problem': problem,
        'editorial': editorial
    })

@login_required(login_url='/login/')
def problem_discussions(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    discussions = problem.discussions.all().order_by('-created_at')
    if request.method == 'POST':
        title = request.POST.get('title')
        body = request.POST.get('body')
        if title and body:
            Discussion.objects.create(
                problem=problem,
                user=request.user,
                title=title,
                body=body
            )
            return redirect('problem_discussions', problem_id=problem.id)
    return render(request, 'judge/discussions.html', {
        'problem': problem,
        'discussions': discussions
    })

@login_required(login_url='/login/')
def discussion_detail(request, pk):
    discussion = get_object_or_404(Discussion, pk=pk)
    if request.method == 'POST':
        body = request.POST.get('body')
        if body:
            Comment.objects.create(
                discussion=discussion,
                user=request.user,
                body=body
            )
            return redirect('discussion_detail', pk=discussion.pk)
    return render(request, 'judge/discussion_detail.html', {
        'discussion': discussion
    })

@staff_member_required
def delete_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    problem.delete()
    return redirect('problem_list')

def verify_email(request, token):
    try:
        profile = UserProfile.objects.get(email_token=token)
        profile.email_verified = True
        profile.email_token = ''
        profile.user.is_active = True
        profile.user.save()
        profile.save()
        return render(request, 'judge/email_verified_success.html')
    except UserProfile.DoesNotExist:
        return render(request, 'judge/email_verified_failed.html')

@login_required(login_url='/login/')
def upload_avatar(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        if 'profile_pic' in request.FILES:
            profile.profile_pic = request.FILES['profile_pic']
            profile.save()
            return redirect('profile') 
    return render(request, 'judge/profile.html', {'profile': profile})    

@login_required(login_url='/login/')
def remove_avatar(request):
    if request.method == 'POST':
        user_profile = get_object_or_404(UserProfile, user=request.user)
        if user_profile.profile_pic:
            user_profile.profile_pic.delete(save=False)
            user_profile.profile_pic = None
            user_profile.save()
            
    return redirect('profile')   
 
@login_required(login_url='/login/')
def monthly_leaderboard_view(request):
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    profiles = UserProfile.objects.annotate(
        monthly_solved=Count(
            'user__submission',
            filter=Q(user__submission__status='Accepted', user__submission__submitted_at__gte=start_of_month),
            distinct=True
        )
    ).order_by('-monthly_solved', '-score', '-rating')
    
    return render(request, 'judge/monthly_leaderboard.html', {'profiles': profiles})

def update_user_streak(user):
    profile, created = UserProfile.objects.get_or_create(user=user)
    today = date.today()
    
    if profile.last_submission_date == today:
        return  
        
    if profile.last_submission_date == today - timedelta(days=1):
        profile.streak += 1  
    elif profile.last_submission_date is None or profile.last_submission_date < today - timedelta(days=1):
        profile.streak = 1   
        
    profile.last_submission_date = today
    profile.save()

@login_required(login_url='/login/')
def ai_tools_view(request):
    return render(request, 'judge/ai_tools.html')

@login_required(login_url='/login/')
def practice_workspace_view(request):
    bookmarks = UserWorkspace.objects.filter(user=request.user, item_type='BOOKMARK')
    favourites = UserWorkspace.objects.filter(user=request.user, item_type='FAVOURITE')
    notes = UserWorkspace.objects.filter(user=request.user, item_type='NOTE')
    recent = UserWorkspace.objects.filter(user=request.user, item_type='RECENT')
    
    context = {
        'bookmarks': bookmarks,
        'favourites': favourites,
        'notes': notes,
        'recent': recent,
    }
    return render(request, 'judge/practice_workspace.html', context)

@login_required(login_url='/login/')
def add_comment(request, model_name, pk):
    if request.method == 'POST':
        text = request.POST.get('text')
        model_type = ContentType.objects.get(model=model_name)
        if text:
            Comment.objects.create(
                user=request.user,
                content_type=model_type,
                object_id=pk,
                text=text
            )
    return redirect(request.META.get('HTTP_REFERER', 'problem_list'))

@login_required(login_url='/login/')
def add_reply(request, comment_id):
    if request.method == 'POST':
        text = request.POST.get('text')
        comment = get_object_or_404(Comment, id=comment_id)
        if text:
            Reply.objects.create(
                comment=comment,
                user=request.user,
                text=text
            )
    return redirect(request.META.get('HTTP_REFERER', 'problem_list'))

@login_required(login_url='/login/')
def handle_vote(request, model_name, pk, vote_val):
    model_type = ContentType.objects.get(model=model_name)
    vote_obj, created = Vote.objects.get_or_create(
        user=request.user,
        content_type=model_type,
        object_id=pk,
        defaults={'vote_type': vote_val}
    )
    if not created:
        if vote_obj.vote_type == vote_val:
            vote_obj.delete() 
        else:
            vote_obj.vote_type = vote_val
            vote_obj.save()
    return redirect(request.META.get('HTTP_REFERER', 'problem_list'))

@login_required(login_url='/login/')
def user_activity_heatmap(request):
    start_date = date.today() - timedelta(days=365)
    activities = (
        Submission.objects.filter(user=request.user, submitted_at__date__gte=start_date)
        .annotate(date=TruncDate('submitted_at'))
        .values('date')
        .annotate(count=Count('id'))
    )
    activity_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in activities if item['date']}
    context = {'activity_dict': activity_dict}
    return render(request, 'judge/heatmap.html', context)

@login_required(login_url='/login/')
def topic_wise_progress(request):
    solved_submissions = Submission.objects.filter(user=request.user, status='Accepted').select_related('problem')
    topic_stats = {}
    for sub in solved_submissions:
        problem = sub.problem
        tags = [tag.strip() for tag in problem.tags.split(',')] if problem.tags else ['General']
        for tag in tags:
            if tag not in topic_stats:
                topic_stats[tag] = {'total': 0, 'solved': 0}
            topic_stats[tag]['solved'] += 1

    context = {'topic_stats': topic_stats}
    return render(request, 'judge/topic_progress.html', context)

@login_required(login_url='/login/')
def company_sheet(request, company_name):
    problems = Problem.objects.filter(company_tag__iexact=company_name)
    context = {'problems': problems, 'company_name': company_name}
    return render(request, 'judge/company_sheet.html', context)

@login_required(login_url='/login/')
def dashboard_view(request):
    user_badges = UserBadge.objects.filter(user=request.user)
    context = {'user_badges': user_badges}
    return render(request, 'judge/dashboard.html', context)

@login_required(login_url='/login/')
def generate_certificate(request):
    context = {'certificate_user': request.user}
    return render(request, 'judge/certificate.html', context)

@login_required(login_url='/login/')
def analytics_dashboard(request):
    total_users = User.objects.count()
    total_problems = Problem.objects.count()
    total_submissions = Submission.objects.count()
    
    context = {
        'total_users': total_users,
        'total_problems': total_problems,
        'total_submissions': total_submissions,
    }
    return render(request, 'judge/analytics.html', context)

@login_required(login_url='/login/')
def ai_problem_recommendation(request):
    user = request.user
    solved_problems = Submission.objects.filter(user=user, status='Accepted').values_list('problem__title', flat=True).distinct()
    all_problems = Problem.objects.exclude(title__in=solved_problems).values('id', 'title', 'difficulty', 'tags')
    
    problems_list_str = "\n".join([f"- ID: {p['id']}, Title: {p['title']}, Difficulty: {p['difficulty']}, Tags: {p['tags']}" for p in all_problems[:30]])
    
    recommendations = ""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert coding mentor. Based on the user's unsolved problems list provided, recommend 3 best problems for them to practice next and briefly explain why."
                },
                {
                    "role": "user",
                    "content": f"Already solved problems count: {len(solved_problems)}\nHere is a list of available unsolved problems:\n{problems_list_str}"
                }
            ],
            "temperature": 0.7
        }
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            recommendations = data["choices"][0]["message"]["content"]
        else:
            recommendations = "Could not generate recommendations at the moment."
    except Exception as e:
        recommendations = f"Error: {str(e)}"

    return render(request, 'judge/ai_recommendations.html', {'recommendations': recommendations})

def test_redis_view(request):
    cache.set('test_key', 'Redis is working perfectly!')
    val = cache.get('test_key')
    return HttpResponse(f"Redis Test Output: {val}")

def submit_code_view(request):
    print(">>> SUBMIT CODE VIEW IS CALLED! <<<")
    sample_code = 'print("Hello, Online Judge!")'
    
    user = request.user if request.user.is_authenticated else None
    problem = Problem.objects.first()
    
    if not user or not problem:
        return HttpResponse("Please log in and ensure a problem exists to submit code.", status=400)
    
    submission = Submission.objects.create(
        user=user,
        problem=problem,
        code=sample_code,
        language="python",
        status="Pending"
    )
    
    execute_code_task.delay(submission.id, sample_code)
    
    log_user_action(request.user, "Submitted Code", request, details=f"Problem ID: {problem.id}")
    
    return HttpResponse(f"Submission {submission.id} successfully created and sent for execution!")

@staff_member_required
def audit_logs_view(request):
    logs = AuditLog.objects.all().order_by('-time')
    return render(request, 'judge/audit_logs.html', {'logs': logs})

def home_view(request):
    return render(request, 'home.html')  

def roadmap_list(request):
    roadmaps = Roadmap.objects.all()
    return render(request, 'roadmaps/roadmap_list.html', {'roadmaps': roadmaps})

def roadmap_detail(request, slug):
    roadmap = get_object_or_404(Roadmap, slug=slug)
    steps = roadmap.steps.prefetch_related('problems').order_by('order')
    return render(request, 'roadmaps/roadmap_detail.html', {'roadmap': roadmap, 'steps': steps})

@staff_member_required
def admin_analytics_dashboard(request):
    total_users = User.objects.count()
    total_problems = Problem.objects.count()
    total_submissions = Submission.objects.count()
    accepted_submissions = Submission.objects.filter(status='Accepted').count()
    
    context = {
        'total_users': total_users,
        'total_problems': total_problems,
        'total_submissions': total_submissions,
        'accepted_submissions': accepted_submissions,
    }
    return render(request, 'admin/analytics_dashboard.html', context)

@login_required(login_url='/login/')
def admin_analytics_dashboard(request):
    total_users = User.objects.count()
    total_problems = Problem.objects.count()
    total_submissions = Submission.objects.count()
    accepted_submissions = Submission.objects.filter(status='Accepted').count()
    
    submissions_by_date = (
        Submission.objects.annotate(date=TruncDate('submitted_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    data_list = []
    for item in submissions_by_date:
        if item['date']:
            data_list.append({
                'date': item['date'].strftime('%Y-%m-%d'),
                'count': item['count']
            })

    language_data = (
        Submission.objects.values('language')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    lang_labels = [item['language'] for item in language_data]
    lang_counts = [item['count'] for item in language_data]

    context = {
        'total_users': total_users,
        'total_problems': total_problems,
        'total_submissions': total_submissions,
        'accepted_submissions': accepted_submissions,
        'submissions_by_date': data_list,
        'lang_labels': lang_labels,
        'lang_counts': lang_counts,
    }
    return render(request, 'admin/analytics_dashboard.html', context)

@login_required(login_url='/login/')
def contest_list(request):
    return render(request, 'judge/contest_list.html')