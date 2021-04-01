import pytest
from smartsim.launcher.stepInfo import *
from smartsim import constants

def test_str():
    step_info = StepInfo(status=constants.STATUS_COMPLETED, launcher_status="COMPLETED", returncode=0)
    expected_output = "Status: Completed | Launcher Status COMPLETED | Returncode 0"

    assert(str(step_info) == expected_output)

def test_default():
    step_info = UnmanagedStepInfo()

    assert(step_info._get_smartsim_status(None) == constants.STATUS_FAILED)

    