from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
import yt_dlp
from .models import BlogPost
import os
import assemblyai as aai
import openai
import re


def sanitize_filename(filename):
    # Remove invalid characters from the filename
    return re.sub(r'[<>:"/\\|?*]', '', filename)

# Download YouTube video as audio and convert to MP3
def download_audio(link):
    try:    
        # Ensure the media directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(id)s.%(ext)s'),
            'postprocessors': [],  # Remove post-processing
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            return os.path.join(settings.MEDIA_ROOT, f"{info['id']}.{info['ext']}"), info['title']

    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None, None

# Transcribe audio file using AssemblyAI
def get_transcription(link):
    aai.settings.api_key = os.environ.get('ASSEMBLYAI_API_KEY')
    audio_file, video_title = download_audio(link)
    if not audio_file:
        return None, None

    transcriber = aai.Transcriber()
    try:
        print(f"Attempting to transcribe file: {audio_file}")
        transcript = transcriber.transcribe(audio_file)
        return transcript.text, video_title
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None, video_title

# Generate blog content from transcription using OpenAI
def generate_blog_from_transcription(transcription):
    # Make Changes add Vector DB
    # so I get all the audio but its too long so store in a vector DB 
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that writes blog articles based on provided transcripts."
        },
        {
            "role": "user",
            "content": f"Based on the following transcript from a YouTube video, write a comprehensive blog article. Make it look like a well-structured blog, not a YouTube transcript:\n\n{transcription}\n\nArticle:"
        }
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        generated_content = response.choices[0].message['content'].strip()
        return re.sub(r'#\s+', '  ', generated_content)
    except Exception as e:
        print(f"Error generating blog content: {e}")
        return None

@login_required  # Ensures that only authenticated users can access this view
def blog_list(request):
    # Retrieve blog posts for the logged-in user
    blog_articles = BlogPost.objects.filter(user=request.user)

    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data.get('link')
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        transcription, video_title = get_transcription(yt_link)
        print(f'Transcript: {transcription}')

        if not video_title:
            return JsonResponse({'error': 'Failed to retrieve video title'}, status=500)

        if not transcription:
            return JsonResponse({'error': 'Failed to get transcript and Video Title'}, status=500)

        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': 'Failed to generate blog article'}, status=500)
        # Saving into Database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=video_title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()

        # return blog article to response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'login.html', {'error_message': 'Invalid username or password'})
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeat_password = request.POST['repeatPassword']

        if password == repeat_password:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except Exception as e:
                return render(request, 'signup.html', {'error_message': 'Error creating account'})
        else:
            return render(request, 'signup.html', {'error_message': 'Passwords do not match'})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

@login_required
def blog_details(request, blog_id):
    print(f"Accessing blog details for ID: {blog_id}")  # Debug output
    blog_article_detail = BlogPost.objects.get(id=blog_id)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return render('/')



