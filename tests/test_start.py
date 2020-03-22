import os

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_gtk_show_and_get_title():
    from fah import FAHControl

    glade = os.path.join(BASE_DIR, 'fah/FAHControl.glade')

    fah_control = FAHControl(glade)
    window = fah_control.window
    window.show()
    assert window.get_title() == "FAHControl - Folding@home Client Advanced Control"
    window.destroy()


@pytest.mark.skip('For integration testing')
def test_start_and_quit():
    from fah import FAHControl
    glade = os.path.join(BASE_DIR, 'fah/FAHControl.glade')
    fah_control = FAHControl(glade)
    with pytest.raises(SystemExit):
        fah_control.run()
