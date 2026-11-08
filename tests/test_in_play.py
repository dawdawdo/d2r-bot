from bot.nav import CENTER, PLAY, in_play


def test_inside_unchanged():
    assert in_play(-350, -60) == (-350, -60)


def test_hud_hop_shortened_same_direction():
    dx, dy = in_play(13, 368)  # back_to's 2026-11-08 failure: click at y 698 (HUD)
    assert CENTER[1] + dy <= PLAY[3]
    assert abs(dx / dy - 13 / 368) < 1e-9


def test_all_edges():
    for v in [(-900, 0), (900, 0), (0, -500), (0, 500), (700, 400), (-700, -400)]:
        dx, dy = in_play(*v)
        assert PLAY[0] <= CENTER[0] + dx <= PLAY[2] and PLAY[1] <= CENTER[1] + dy <= PLAY[3]
