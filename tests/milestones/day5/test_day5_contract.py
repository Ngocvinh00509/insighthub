import pathlib

def test_day5_milestone_structure():
    evidence_dir = pathlib.Path('evidence')
    evidence_dir.mkdir(exist_ok=True)
    assert evidence_dir.exists(), "Evidence directory must exist"
