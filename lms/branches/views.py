from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Branch, Section
from .forms import BranchForm, SectionForm
from library.models import Book
from borrow.models import Borrowing

def is_manager(user):
    return user.is_authenticated and user.role in ['manager', 'admin']

@login_required
@user_passes_test(is_manager)
@login_required
@user_passes_test(is_manager)
def manage_branches(request):
    """Main branch management dashboard with filtering and search"""
    
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to manage branches.")
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    location_filter = request.GET.get('location', '')
    sections_filter = request.GET.get('sections', '')
    
    # Base queryset with annotations
    branches = Branch.objects.annotate(
        section_count=Count('section'),
        book_count=Count('book', distinct=True),
        active_borrowings=Count('book__borrowing', filter=Q(book__borrowing__status='active'), distinct=True)
    )
    
    # Apply filters
    if search_query:
        branches = branches.filter(
            Q(branch_name__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    if location_filter:
        branches = branches.filter(location=location_filter)
    
    if sections_filter:
        if sections_filter == '0':
            branches = branches.filter(section_count=0)
        elif sections_filter == '1-5':
            branches = branches.filter(section_count__gte=1, section_count__lte=5)
        elif sections_filter == '6-10':
            branches = branches.filter(section_count__gte=6, section_count__lte=10)
        elif sections_filter == '10+':
            branches = branches.filter(section_count__gt=10)
    
    # Order by branch name
    branches = branches.order_by('branch_name')
    
    # Pagination
    paginator = Paginator(branches, 20)  # 20 branches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate metrics
    total_branches = Branch.objects.count()
    total_sections = Section.objects.count()
    total_books = Book.objects.count()
    active_borrowings = Borrowing.objects.filter(status='active').count()
    
    # Branch distribution by location
    location_distribution = Branch.objects.values('location').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate percentages for location distribution
    total_for_percentage = sum(location['count'] for location in location_distribution)
    for location in location_distribution:
        location['percentage'] = round((location['count'] / total_for_percentage) * 100) if total_for_percentage > 0 else 0
    
    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    recent_borrowings = Borrowing.objects.filter(
        borrow_date__gte=thirty_days_ago
    ).count()
    
    # Section statistics
    branches_with_sections = Branch.objects.filter(section__isnull=False).distinct().count()
    branches_without_sections = total_branches - branches_with_sections
    
    # Book distribution
    branches_with_books = Branch.objects.filter(book__isnull=False).distinct().count()
    branches_without_books = total_branches - branches_with_books
    
    context = {
        'branches': page_obj,
        'total_branches': total_branches,
        'total_sections': total_sections,
        'total_books': total_books,
        'active_borrowings': active_borrowings,
        'location_distribution': location_distribution,
        'recent_borrowings': recent_borrowings,
        'branches_with_sections': branches_with_sections,
        'branches_without_sections': branches_without_sections,
        'branches_with_books': branches_with_books,
        'branches_without_books': branches_without_books,
    }
    
    return render(request, 'manage_branches.html', context)
@login_required
@user_passes_test(is_manager)
def create_branch(request):
    """Create a new branch"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to create branches.")
    
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            messages.success(request, f'Branch "{branch.branch_name}" created successfully!')
            return redirect('branches:manage_branches')
        else:
            messages.error(request, "Failed to create branch. Please correct the errors.")
    else:
        form = BranchForm()
    
    return render(request, 'branch_form.html', {
        'form': form,
        'title': 'Create New Branch',
        'submit_text': 'Create Branch'
    })

@login_required
@user_passes_test(is_manager)
def edit_branch(request, branch_id):
    """Edit an existing branch"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to edit branches.")
    
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        messages.error(request, 'Branch not found.')
        return redirect('branches:manage_branches')
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Branch "{branch.branch_name}" updated successfully!')
            return redirect('branches:manage_branches')
        else:
            messages.error(request, "Failed to update branch. Please correct the errors.")
    else:
        form = BranchForm(instance=branch)
    
    return render(request, 'branch_form.html', {
        'form': form,
        'branch': branch,
        'title': 'Edit Branch',
        'submit_text': 'Update Branch'
    })

@login_required
@user_passes_test(is_manager)
def delete_branch(request, branch_id):
    """Delete a branch"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to delete branches.")
    
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        messages.error(request, 'Branch not found.')
        return redirect('branches:manage_branches')
    
    if request.method == 'POST':
        branch_name = branch.branch_name
        branch.delete()
        messages.success(request, f'Branch "{branch_name}" deleted successfully!')
        return redirect('branches:manage_branches')
    
    return render(request, 'branch_delete_confirm.html', {
        'branch': branch
    })

@login_required
@user_passes_test(is_manager)
def manage_sections(request):
    """Manage sections within branches with filtering and search"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to manage sections.")
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    branch_filter = request.GET.get('branch', '')
    
    # Base queryset with annotations
    sections = Section.objects.select_related('branch_id').annotate(
        book_count=Count('branch_id__book', distinct=True)
    )
    
    # Apply filters
    if search_query:
        sections = sections.filter(
            Q(name__icontains=search_query) |
            Q(branch_id__branch_name__icontains=search_query) |
            Q(branch_id__location__icontains=search_query)
        )
    
    if branch_filter:
        sections = sections.filter(branch_id_id=branch_filter)
    
    # Order by branch name, then section name
    sections = sections.order_by('branch_id__branch_name', 'name')
    
    # Pagination
    paginator = Paginator(sections, 20)  # 20 sections per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_sections = Section.objects.count()
    total_branches = Branch.objects.count()
    sections_with_books = Section.objects.filter(branch_id__book__isnull=False).distinct().count()
    sections_without_books = total_sections - sections_with_books
    
    # Branch statistics for sections
    branches = Branch.objects.all()
    
    # Average sections per branch
    avg_sections_per_branch = round(total_sections / total_branches, 1) if total_branches > 0 else 0
    
    context = {
        'sections': page_obj,
        'total_sections': total_sections,
        'total_branches': total_branches,
        'branches': branches,
        'sections_with_books': sections_with_books,
        'sections_without_books': sections_without_books,
        'avg_sections_per_branch': avg_sections_per_branch,
    }
    
    return render(request, 'manage_sections.html', context)

@login_required
@user_passes_test(is_manager)
def create_section(request):
    """Create a new section"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to create sections.")
    
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save()
            messages.success(request, f'Section "{section.name}" created successfully!')
            return redirect('branches:manage_sections')
        else:
            messages.error(request, "Failed to create section. Please correct the errors.")
    else:
        form = SectionForm()
    
    return render(request, 'section_form.html', {
        'form': form,
        'title': 'Create New Section',
        'submit_text': 'Create Section'
    })

@login_required
@user_passes_test(is_manager)
def edit_section(request, section_id):
    """Edit an existing section"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to edit sections.")
    
    try:
        section = Section.objects.get(id=section_id)
    except Section.DoesNotExist:
        messages.error(request, 'Section not found.')
        return redirect('branches:manage_sections')
    
    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, f'Section "{section.name}" updated successfully!')
            return redirect('branches:manage_sections')
        else:
            messages.error(request, "Failed to update section. Please correct the errors.")
    else:
        form = SectionForm(instance=section)
    
    return render(request, 'section_form.html', {
        'form': form,
        'section': section,
        'title': 'Edit Section',
        'submit_text': 'Update Section'
    })

@login_required
@user_passes_test(is_manager)
def delete_section(request, section_id):
    """Delete a section"""
    if request.user.role != 'manager':
        return HttpResponseForbidden("You don't have permission to delete sections.")
    
    try:
        section = Section.objects.get(id=section_id)
    except Section.DoesNotExist:
        messages.error(request, 'Section not found.')
        return redirect('branches:manage_sections')
    
    if request.method == 'POST':
        section_name = section.name
        section.delete()
        messages.success(request, f'Section "{section_name}" deleted successfully!')
        return redirect('branches:manage_sections')
    
    return render(request, 'section_delete_confirm.html', {
        'section': section
    })
