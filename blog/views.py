from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.contrib.postgres.search import TrigramSimilarity

from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm
from taggit.models import Tag
from django.db.models import Count

"""class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 1
"""
def post_list(request, tag_slug=None):
    form = SearchForm()
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])
    paginator = Paginator(object_list, 3)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post_list.html', {'page': page, 'posts': posts, 'tag': tag, 'form':form})

def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published', publish__year=year,
                             publish__month=month, publish__day=day)
    # Список активных комментариев для этой статьи.
    comments = Comment.objects.filter(post=post, active=True)
    new_comment = None
    if request.method=='POST':
        # Пользователь отправил комментарий.
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Создаем комментарий, но пока не сохраняем в базе данных.
            new_comment = comment_form.save(commit=False)
            # Привязываем комментарий к текущей статье.
            new_comment.post=post
            # Сохраняем комментарий в базе данных.
            new_comment.save()
    else:
        comment_form = CommentForm()

    # Формирование списка похожих статей.
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:3]

    return render(request, 'blog/post_detail.html', {'post': post,'comments':comments,
                                                     'new_comment':new_comment,'comment_form':comment_form,
                                                     'similar_posts': similar_posts,})

def post_share(request, post_id):

    # Получение статьи по идентификатору.
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    if request.method=='POST':
        # Форма была отправлена на сохранение
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Все поля формы прошли валидацию.
            cd = form.cleaned_data

            # Отправка электронной почты.
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f'{cd["name"]} ({cd["email"]}) recommends you reading "{post.title}"'
            message = f'Read "{post.title}" at {post_url}\n\n {cd["name"]}\'s comments: {cd["comment"]}'
            send_mail(subject, message, 'thisisumurzakov@gmail.com', (cd['to'],))
            sent = True
        else:
            form = EmailPostForm()
            return render(request, 'blog/post_share.html', {'post':post,'form':form, 'sent':sent})
    return render(request, 'blog/post_share.html', {'post': post, 'sent': sent})

def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data['query']
        results = Post.published.annotate(similarity=TrigramSimilarity('title', query))\
            .filter(similarity__gt=0.3).order_by('-similarity')
        #results = Post.published.annotate(search=SearchVector('title','body')).filter(search=query)
    return render(request, 'blog/post_search.html', {'form': form, 'query': query, 'results': results})

def search_base(requset):
    form = SearchForm()
    return render(requset, 'base.html', {'form':form})