from django.contrib import admin
from .models import (Board, Column, Task, Sprint, RetroNote, BoardMember, Label,
                     ChecklistItem, Comment, Attachment, Activity, Notification)
admin.site.register([Board, Column, Task, Sprint, RetroNote, BoardMember, Label,
                     ChecklistItem, Comment, Attachment, Activity, Notification])
