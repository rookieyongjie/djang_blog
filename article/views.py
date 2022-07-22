from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect

from comment.forms import CommentForm
from comment.models import Comment
from .models import ArticlePost, ArticleColumn
import markdown
from .forms import ArticlePostForm
from django.contrib.auth.models import User
from django.db.models import Q
from django_blog.settings import LOGGING
import logging

logging.config.dictConfig(LOGGING)
logger = logging.getLogger('django.request')


# def article_list(request):
# search = request.GET.get('search')
# order = request.GET.get('order')
# column = request.GET.get('column')
# tag = request.GET.get('tag')
# # 初始化查询集
# article_list = ArticlePost.objects.all()
# # 用户搜索逻辑
# if search:
#     if order == 'total_views':
#         # 用 Q对象 进行联合搜索
#         article_list = ArticlePost.objects.filter(
#             Q(title__icontains=search) |
#             Q(body__icontains=search)
#         ).order_by('-total_views')
#     else:
#         article_list = ArticlePost.objects.filter(
#             Q(title__icontains=search) |
#             Q(body__icontains=search)
#         )
# else:
#     # 将 search 参数重置为空
#     search = ''
#     if order == 'total_views':
#         article_list = ArticlePost.objects.all().order_by('-total_views')
#     else:
#         article_list = ArticlePost.objects.all()
#
# # 每页显示 1 篇文章
# paginator = Paginator(article_list, 2)
# # 获取 url 中的页码
# page = request.GET.get('page', 1)
# # 将导航对象相应的页码内容返回给 articles
# articles = paginator.get_page(page)
# context = {'articles': articles, 'order': order, 'search': search}
# return render(request, 'article/list.html', context)


# 文章详情
def article_list(request):
    # 从 url 中提取查询参数
    search = request.GET.get('search')
    order = request.GET.get('order')
    column = request.GET.get('column')
    tag = request.GET.get('tag')
    # 初始化查询集
    article_list = ArticlePost.objects.all()
    # 搜索查询集
    if search:
        article_list = article_list.filter(
            Q(title__icontains=search) |
            Q(body__icontains=search)
        )
    else:
        search = ''

    # 栏目查询集
    if column is not None and column.isdigit():
        article_list = article_list.filter(column=column)

    # 标签查询集
    if tag and tag != 'None':
        article_list = article_list.filter(tags__name__in=[tag])

    # 查询集排序
    if order == 'total_views':
        article_list = article_list.order_by('-total_views')
    paginator = Paginator(article_list, 3)
    page = request.GET.get('page')
    articles = paginator.get_page(page)

    # 需要传递给模板（templates）的对象
    context = {
        'articles': articles,
        'order': order,
        'search': search,
        'column': column,
        'tag': tag,
    }
    return render(request, 'article/list.html', context)


def article_detail(request, id):
    article = ArticlePost.objects.get(id=id)
    # 取出文章评论
    comments = Comment.objects.filter(article=id)
    if request.user != article.author:
        article.total_views += 1
        article.save(update_fields=['total_views'])
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
        ]
    )
    article.body = md.convert(article.body)
    comment_form = CommentForm()
    # 新增了md.toc对象
    context = {'comment_form': comment_form, 'article': article, 'toc': md.toc, 'comments': comments}
    return render(request, 'article/detail.html', context)


# 写文章的视图
def article_create(request):
    # 判断用户是否提交数据
    if request.method == "POST":
        article_post_form = ArticlePostForm(request.POST, request.FILES)
        if article_post_form.is_valid():
            new_article = article_post_form.save(commit=False)
            new_article.author = User.objects.get(id=request.user.id)
            if request.POST['column'] != 'none':
                new_article.column = ArticleColumn.objects.get(id=request.POST['column'])
            new_article.save()
            article_post_form.save_m2m()
            return redirect('article:article_list')
        else:
            return HttpResponse('表单内容有误，请重新填写')
    # 如果用户请求获取数据
    else:
        # 创建表单类实例
        article_post_form = ArticlePostForm()
        columns = ArticleColumn.objects.all()
        # 赋值上下文
        context = {'article_post_form': article_post_form, 'columns': columns}
        # 返回模板
        return render(request, 'article/create.html', context)


# # 删除文章
# def article_delete(request, id):
#     article = ArticlePost.objects.get(id=id)
#     article.delete()
#     return redirect("article:article_list")


# 安全删除文章
def article_safe_delete(request, id):
    if request.method == 'POST':
        article = ArticlePost.objects.get(id=id)
        article.delete()
        return redirect('article:article_list')
    else:
        return HttpResponse('仅允许post请求')


def article_update(request, id):
    article = ArticlePost.objects.get(id=id)
    # 过滤非作者的用户
    if request.user != article.author:
        return HttpResponse("抱歉，你无权修改这篇文章。")
    if request.method == "POST":
        article_post_form = ArticlePostForm(data=request.POST)
        if article_post_form.is_valid():
            article.title = request.POST['title']
            article.body = request.POST['body']
            if request.POST['column'] != 'none':
                article.column = ArticleColumn.objects.get(id=request.POST['column'])
            else:
                article.column = None
            if request.FILES.get('avatar'):
                article.avatar = request.FILES.get('avatar')
            article.tags.set(*request.POST.get('tags').split(','), clear=True)
            article.save()
            return redirect('article:article_detail', id=id)
        else:
            return HttpResponse('表单内容有误，请重新填写')
    else:
        article_post_form = ArticlePostForm()
        columns = ArticleColumn.objects.all()
        context = {'article': article,
                   'article_post_form': article_post_form,
                   'columns': columns,
                   'tags': ','.join([x for x in article.tags.names()]),
                   }
        return render(request, 'article/update.html', context)
