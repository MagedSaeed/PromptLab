# prompt/templatetags/pagination_tags.py

from django import template

register = template.Library()


@register.simple_tag
def pagination_range(page_obj, num_pages=5):
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages

    start_page = max(current_page - num_pages // 2, 1)
    end_page = min(current_page + num_pages // 2, total_pages)

    if end_page - start_page < num_pages:
        if start_page == 1:
            end_page = min(num_pages, total_pages)
        elif end_page == total_pages:
            start_page = max(total_pages - num_pages + 1, 1)

    page_numbers = list(range(start_page, end_page + 1))

    if start_page > 2:
        page_numbers.insert(0, "...")
        page_numbers.insert(0, 1)

    if end_page < total_pages - 1:
        page_numbers.append("...")
        page_numbers.append(total_pages)

    return page_numbers
