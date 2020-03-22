import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_start_client():
    from fah import FAHControl

    glade = os.path.join(BASE_DIR, 'fah/FAHControl.glade')

    fah_control = FAHControl(glade)
    window = fah_control.window
    window.show()
    assert window.get_title() == "FAHControl - Folding@home Client Advanced Control"
    window.destroy()

    # TODO: run
    # TODO: quit
