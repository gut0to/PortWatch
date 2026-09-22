from portwatch.presentation.tables import watch_view


def test_watch_view_is_a_composite_renderable() -> None:
    view = watch_view([], 2.0)

    assert len(view.renderables) == 2
