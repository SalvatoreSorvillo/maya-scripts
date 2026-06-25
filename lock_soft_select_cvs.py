"""Pin (lock) the first CV(s) of curves so soft-selection edits don't drag them.

Maya has no native "exclude this CV from soft selection" option -- the falloff
always weights neighbours by distance. This tool stores the world position of
the first CV(s) of each curve you're editing and keeps an idle scriptJob running
that snaps them back whenever they drift. So you can turn soft selection on and
move the last CV(s) of a curve while the first CV(s) stay locked in place.

Workflow (Maya 2023+):
    1. Select the CV(s) you want to MOVE (e.g. the last CV of each curve).
    2. import lock_soft_select_cvs as L
       L.lock_first_cvs()           # pins CV index 0 of each curve involved
    3. Turn soft selection on and move your selected CVs. The first CV(s) hold.
    4. L.unlock_first_cvs()          # release the lock when finished

Options:
    L.lock_first_cvs(count=2)        # lock the first two CVs of each curve
    L.lock_first_cvs(curves=["hair_01", "hair_02"])
    L.restore_now()                 # one-shot snap back, no scriptJob

Note: while you actively drag a CV, Maya may not fire idle events until you
pause or release, so a pinned CV can flick and then snap back. That is the best
a script can do without a custom manipulator -- the final result is locked.
"""

import maya.cmds as cmds

_PINNED = {}          # cv name -> (x, y, z) stored world position
_JOB = None           # idle scriptJob id
_EPS = 1e-6           # ignore sub-micron drift so a stable rig does no work


def _curve_shapes_from_selection():
    sel = cmds.ls(selection=True, long=True, flatten=True) or []
    shapes = set()
    for item in sel:
        node = item.split(".")[0] if "." in item else item
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) == "nurbsCurve":
            shapes.add(node)
            continue
        sh = cmds.listRelatives(node, shapes=True, type="nurbsCurve",
                                noIntermediate=True, fullPath=True) or []
        shapes.update(sh)
    return sorted(shapes)


def _shapes_from_arg(curves):
    shapes = []
    for c in curves:
        if not cmds.objExists(c):
            continue
        if cmds.nodeType(c) == "nurbsCurve":
            shapes.append(c)
        else:
            shapes += cmds.listRelatives(c, shapes=True, type="nurbsCurve",
                                         noIntermediate=True, fullPath=True) or []
    return shapes


def _num_cvs(shape):
    spans = cmds.getAttr(shape + ".spans")
    degree = cmds.getAttr(shape + ".degree")
    form = cmds.getAttr(shape + ".form")  # 0 open, 1 closed, 2 periodic
    return spans if form == 2 else spans + degree


def lock_first_cvs(curves=None, count=1):
    """Store and pin the first `count` CV(s) of each curve you are editing."""
    global _PINNED
    shapes = _shapes_from_arg(curves) if curves else _curve_shapes_from_selection()
    if not shapes:
        raise RuntimeError("No NURBS curves found. Select the CV(s) you want to "
                           "move first, or pass curves=[...].")

    _PINNED = {}
    for shape in shapes:
        n = _num_cvs(shape)
        for i in range(min(count, n)):
            cv = "{}.cv[{}]".format(shape, i)
            pos = cmds.pointPosition(cv, world=True)
            _PINNED[cv] = (pos[0], pos[1], pos[2])

    _start_job()
    print("Locked {} CV(s) across {} curve(s). Run unlock_first_cvs() to release."
          .format(len(_PINNED), len(shapes)))
    return len(_PINNED)


def restore_now():
    """Snap any drifted pinned CVs back to their stored position (one pass)."""
    if not _PINNED:
        return
    to_fix = []
    for cv, pos in _PINNED.items():
        if not cmds.objExists(cv):
            continue
        cur = cmds.pointPosition(cv, world=True)
        if (abs(cur[0] - pos[0]) > _EPS or abs(cur[1] - pos[1]) > _EPS
                or abs(cur[2] - pos[2]) > _EPS):
            to_fix.append((cv, pos))
    if not to_fix:
        return

    # Keep these corrective moves out of the undo queue so Ctrl+Z still undoes
    # the user's edit, not our pinning.
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        for cv, pos in to_fix:
            cmds.xform(cv, worldSpace=True, translation=pos)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def _start_job():
    global _JOB
    _stop_job()
    _JOB = cmds.scriptJob(event=["idle", restore_now], killWithScene=True)


def _stop_job():
    global _JOB
    if _JOB is not None and cmds.scriptJob(exists=_JOB):
        cmds.scriptJob(kill=_JOB, force=True)
    _JOB = None


def unlock_first_cvs():
    """Release the lock and stop the idle scriptJob."""
    global _PINNED
    _stop_job()
    n = len(_PINNED)
    _PINNED = {}
    print("Released {} locked CV(s).".format(n))
    return n


if __name__ == "__main__":
    lock_first_cvs()
