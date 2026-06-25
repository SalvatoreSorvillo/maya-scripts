"""Snap selected NURBS curve CVs to the closest point on a target mesh.

Hair-groom cleanup helper (Maya 2023.3.4). Only the CVs you have selected are
moved, so to fix just the first CV of each curve, select those CVs and run.

Usage:
    1. Select the CVs to snap.
    2. Shift-select the head geo too (or pass mesh="head_GEO").
    3. import snap_cvs_to_geo; snap_cvs_to_geo.snap_cvs_to_geo()
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om


def snap_cvs_to_geo(mesh=None):
    selection = cmds.ls(selection=True, flatten=True, long=True) or []
    cvs = [i for i in selection if ".cv[" in i]
    if not cvs:
        raise RuntimeError("No curve CVs selected. Select the CVs first.")

    if mesh is None:
        for node in (i for i in selection if ".cv[" not in i):
            if not cmds.objExists(node):
                continue
            if cmds.nodeType(node) == "mesh":
                mesh = node
                break
            sh = cmds.listRelatives(node, shapes=True, type="mesh",
                                    noIntermediate=True, fullPath=True)
            if sh:
                mesh = sh[0]
                break
    if not mesh:
        raise RuntimeError("No target mesh found. Shift-select the head geo too, "
                           "or call snap_cvs_to_geo(mesh=\"head_GEO\").")

    sel = om.MSelectionList()
    sel.add(mesh)
    dag = sel.getDagPath(0)
    if dag.apiType() != om.MFn.kMesh:
        dag.extendToShape()
    if dag.apiType() != om.MFn.kMesh:
        raise RuntimeError("'{}' is not a polygon mesh.".format(mesh))
    fn = om.MFnMesh(dag)

    cmds.undoInfo(openChunk=True)
    try:
        for cv in cvs:
            s = cmds.pointPosition(cv, world=True)
            closest, _ = fn.getClosestPoint(
                om.MPoint(s[0], s[1], s[2]), om.MSpace.kWorld)
            cmds.xform(cv, worldSpace=True,
                       translation=(closest.x, closest.y, closest.z))
    finally:
        cmds.undoInfo(closeChunk=True)

    print("Snapped {} CV(s) onto '{}'.".format(len(cvs), mesh))
    return len(cvs)


if __name__ == "__main__":
    snap_cvs_to_geo()
