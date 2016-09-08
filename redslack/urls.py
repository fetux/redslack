from django.conf.urls import url
from redslack import views

urlpatterns = [
    url(r'^', views.router),
    # url(r'^connect/(?P<url>[A-Za-z]+)/(?P<key>[A-Za-z0-9]+)/$', views.connect),
    # url(r'^todo/$', views.todo),
    # url(r'^issue/(?P<pk>[0-9]+)/$', views.issue_show),
    # url(r'^issue/(?P<pk>[0-9]+)/status/$', views.issue_get_status),
    # url(r'^issue/(?P<pk>[0-9]+)/status/(?P<status>[A-Za-z]+)/$', views.issue_set_status),
    # url(r'^issue/(?P<pk>[0-9]+)/priority/$', views.issue_get_priority),
    # url(r'^issue/(?P<pk>[0-9]+)/priority/(?P<priority>[A-Za-z]+)/$', views.issue_set_priority),
    # url(r'^issue/(?P<pk>[0-9]+)/assignee/$', views.issue_get_assignee),
    # url(r'^issue/(?P<pk>[0-9]+)/assignee/(?P<assignee>[A-Za-z]+)/$', views.issue_set_assignee),
    # url(r'^issue/(?P<pk>[0-9]+)/target/$', views.issue_get_target),
    # url(r'^issue/(?P<pk>[0-9]+)/target/(?P<target>[A-Za-z]+)/$', views.issue_set_target),
    # url(r'^issue/(?P<pk>[0-9]+)/subtasks/$', views.issue_get_subtasks),
    # url(r'^issue/(?P<pk>[0-9]+)/related/$', views.issue_get_related),
    # url(r'^issue/(?P<pk>[0-9]+)/comments/$', views.issue_get_comments),
    # url(r'^issue/(?P<pk>[0-9]+)/comments/(?P<last>[A-Za-z]+)/$', views.issue_get_comments),
    # url(r'^issue/(?P<pk>[0-9]+)/comments/add/(?P<comment>[A-Za-z]+)/$', views.issue_add_comment),
    # url(r'^issue/(?P<pk>[0-9]+)/time/$', views.issue_get_logtime),
    # url(r'^issue/(?P<pk>[0-9]+)/time/(?P<hours>[0-9]+)/(?P<comment>[A-Za-z]+)/$', views.issue_add_logtime),
]