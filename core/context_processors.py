from .views import is_indexable_host


def indexing(request):
    """`noindex` is true on staging and local hosts, so base.html can keep them out of search engines."""
    return {"noindex": not is_indexable_host(request)}
