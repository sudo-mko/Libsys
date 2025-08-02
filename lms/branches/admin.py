from django.contrib import admin
from .models import Branch, Section

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_name', 'location', 'get_section_count', 'get_book_count')
    list_filter = ('location',)
    search_fields = ('branch_name', 'location')
    ordering = ('branch_name',)
    
    def get_section_count(self, obj):
        return obj.section_set.count()
    get_section_count.short_description = 'Sections'
    
    def get_book_count(self, obj):
        return obj.book_set.count()
    get_book_count.short_description = 'Books'

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch_id', 'get_book_count')
    list_filter = ('branch_id', 'branch_id__location')
    search_fields = ('name', 'branch_id__branch_name')
    ordering = ('branch_id__branch_name', 'name')
    
    def get_book_count(self, obj):
        return obj.branch_id.book_set.count()
    get_book_count.short_description = 'Books'
