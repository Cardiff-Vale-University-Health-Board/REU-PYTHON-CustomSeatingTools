import bpy
import mathutils

bl_info = {
    "name": "Cushion Processing Tools",
    "author": "Cardiff Rehabilitation Engineering Unit",
    "version": (0, 0, 0, 4),
    "blender": (3, 5)
}

G_PRINT_DEBUG = True

def calculate_triangle_normal_and_centre(v1, v2, v3):
    a = v2 - v1
    b = v3 - v1
    n = mathutils.Vector((
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    ))
    c = mathutils.Vector((
        v1[0] + v2[0] + v3[0],
        v1[1] + v2[1] + v3[1],
        v1[2] + v2[2] + v3[2],
    )) / 3
    return n, c

def first_non_match(lst, val):
    for index, value in enumerate(lst):
        if value != val:
            return index, value
    return None, None

def set_wireframe_mode(ctx, enable = True):
    for area in ctx.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.overlay.show_wireframes = enable

def transformation_matrix_from_vectors(v1, c1, v2, c2):
    """
    :param v1: A 3d "source" vector
    :param v2: A 3d "destination" vector
    :return mat: A transform matrix (4x4)
    """
    a = v1.normalized()
    b = v2.normalized()
    v = a.cross(b)
    c = a.dot(b)
        
    if(c == -1.0): # vectors are antiparrallel, pick an arbitrary rotation axes and calculate the rotation matrix
        axes = [
            mathutils.Vector((1.0, 0.0, 0.0)),
            mathutils.Vector((0.0, 1.0, 0.0)),
            mathutils.Vector((0.0, 0.0, 1.0))
        ]
        
        dot_products = [a.dot(vec) for vec in axes]
        i, c = first_non_match(dot_products, -1)
        v = a.cross(axes[i])
            
        R = mathutils.Matrix((
            [2*(v[0]*v[0]) - 1, 2*v[0]*v[1], 2*v[0]*v[2]],
            [2*v[0]*v[1], 2*(v[1]*v[1]) - 1, 2*v[1]*v[2]],
            [2*v[0]*v[2], 2*v[1]*v[2], 2*(v[2]*v[2]) - 1]
        ))
        
    elif(c == 1.0): # vectors are parrallel, no rotation required
        R = mathutils.Matrix.Identity(3)
        
    else:
        s = v.magnitude  
        K = mathutils.Matrix((
            [0, -v[2], v[1]],
            [v[2], 0, -v[0]],
            [-v[1], v[0], 0]
        ))    
        K2 = K @ K         
        I = mathutils.Matrix.Identity(3)
        division = (1 - c) / (s*s)
        R = I + K + K2 * division        
    
    R = R.to_4x4()                    
    T = mathutils.Matrix.Translation(c2 - c1)                

    return R @ T

class CREUProperties(bpy.types.PropertyGroup):
    active_tool: bpy.props.EnumProperty(
        items=[
            ("NONE", "None", ""),
            ("IMPORT", "Import", ""),
            ("ALIGN", "Align", ""),
            ("FLIP", "Flip", ""),
            ("REDUCE", "Reduce", ""),
            ("ERASE", "Erase", ""),
            ("HOLES", "Filling Holes", ""),
            ("SMOOTH", "Smooth", ""),
            ("EXPORT", "Export", "")
        ],
        default="NONE",
    )
    import_scale: bpy.props.FloatProperty(
        name = "Scale",
        description = "Scale factor applied to imported meshes",
        default = 0.001,
        min = 0.001,
        soft_max = 1000.0,
        precision = 3
    )

class StartImportOperator(bpy.types.Operator):
    """Import a scanned seat.

    Imprt an unprocessed scan for processing."""

    bl_idname = "creu.start_import"
    bl_label = "Import STL"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "IMPORT"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class StartAlignToOriginOperator(bpy.types.Operator):
    """Align the scan to the XY plane using three selected vertices.
    
    Select three vertices that define the seating surface, then click Align.
    The model will be rotated so that the selected surface lies flat on the
    XY plane and centred at the origin."""

    bl_idname = "creu.start_align"
    bl_label = "Align To Origin Tool"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "ALIGN"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.tool_set_by_id(name="builtin.select_box")
        return {'FINISHED'}

class StartInvertZAxisOperator(bpy.types.Operator):
    """Flip the model about the XY plane.
    
    Use this if the scan is upside down. The model will be rotated 180 degrees so that
    the seating surface faces upward."""

    bl_idname = "creu.start_flip_about_xy"
    bl_label = "Flip Model about XY Plane"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "FLIP"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class StartStandardiseMeshQualityOperator(bpy.types.Operator):
    """Standardise mesh resolution.

    Remesh the scan to produce a more consistent triangle size throughout the model.
    This improves the consistency of editing operations and reduces the number of
    triangles present."""

    bl_idname = "creu.start_mesh_quality"
    bl_label = "Standardise Mesh Resolution"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "REDUCE"
        set_wireframe_mode(context, True)
        bpy.ops.object.mode_set(mode='SCULPT')

        # Select Sculpt Draw tool
        bpy.ops.wm.tool_set_by_id(name="builtin_brush.Draw")

        tool_settings = context.tool_settings

        # Set brush strength to 0
        if tool_settings.sculpt.brush:
            tool_settings.sculpt.brush.strength = 0.0

        # Enable Dyntopo
        if not context.sculpt_object.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()

        # Constant Detail mode
        tool_settings.sculpt.detail_type_method = 'CONSTANT'

        # Detail Resolution
        tool_settings.sculpt.constant_detail_resolution = 50

        return {'FINISHED'}

class StartEraseVerticesOperator(bpy.types.Operator):
    """Delete selected vertices and connected geometry.

    Use this tool to remove unwanted scan artefacts,
    isolated geometry, or areas outside the required seating surface."""

    bl_idname = "creu.start_erasing"
    bl_label = "Erase Vertices"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "ERASE"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.tool_set_by_id(name = "builtin.select_circle")
        return {'FINISHED'}

class StartHoleFillingOperator(bpy.types.Operator):
    """Fill holes in the scan.

    Automatically identify and close gaps in the mesh to create a more
    contiguous surface."""

    bl_idname = "creu.start_hole_filling"
    bl_label = "Fill Holes"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "HOLES"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.tool_set_by_id(name = "builtin.select_box")
        return {'FINISHED'}

class StartSmoothingOperator(bpy.types.Operator):
    """Smooth the surface of the scan.

    Reduce sharp creases and local surface irregularities while preserving
    the overall shape of the cushion."""

    bl_idname = "creu.start_smooth"
    bl_label = "Remove Creases (Smoothing)"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "SMOOTH"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='SCULPT')
        return {'FINISHED'}

class StartExportOperator(bpy.types.Operator):
    """Export the processed model.

    Save the completed scan in a manufacturing-ready format for downstream design,
    machining, or archival purposes."""

    bl_idname = "creu.start_export"
    bl_label = "Export Model"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "EXPORT"
        set_wireframe_mode(context, False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class CancelOperation(bpy.types.Operator):
    """Deselect the current tool."""
    bl_idname = "creu.cancel_operation"
    bl_label = "Cancel"

    def execute(self, context):
        set_wireframe_mode(context, False)

        context.scene.creu.active_tool = "NONE"
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class AlignToOriginOperator(bpy.types.Operator):
    """Aligns an object to the XY plane based on the three currently selected vertices"""
    bl_idname = "creu.align_to_origin"
    bl_label = "Align"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        obj = bpy.context.active_object
        vertices = obj.data.vertices
        selected_vertices = [v for v in vertices if v.select]
        n, c = calculate_triangle_normal_and_centre(
            obj.matrix_world @ selected_vertices[0].co,
            obj.matrix_world @ selected_vertices[1].co,
            obj.matrix_world @ selected_vertices[2].co
        )
        T = transformation_matrix_from_vectors(
            n,
            c,
            mathutils.Vector((0.0, 0.0, 1.0)),
            mathutils.Vector((0.0, 0.0, 0.0))
        )
        obj.matrix_world = T @ obj.matrix_world
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True)
        return self.execute(context)

class InvertZAxisOperator(bpy.types.Operator):
    """Flips an object about the XY plane"""
    bl_idname = "creu.flip_about_xy"
    bl_label = "Flip"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = bpy.context.active_object
        T = transformation_matrix_from_vectors(
            mathutils.Vector((0.0, 0.0, 1.0)),
            mathutils.Vector((0.0, 0.0, 0.0)),
            mathutils.Vector((0.0, 0.0, -1.0)),
            mathutils.Vector((0.0, 0.0, 0.0))
        )
        obj.matrix_world = T @ obj.matrix_world
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True)
        return self.execute(context)

class ScaleImportedMeshOperator(bpy.types.Operator):
    """Scale the selected mesh"""
    bl_idname = "creu.scale_mesh"
    bl_label = "Scale"

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        scale = context.scene.creu.import_scale

        obj.scale = (
            obj.scale.x * scale,
            obj.scale.y * scale,
            obj.scale.z * scale
        )

        bpy.ops.object.transform_apply(scale=True)
        return {'FINISHED'}

class ReduceOperator(bpy.types.Operator):
    """Completes the reduction operation."""
    bl_idname = "creu.reduce_mesh"
    bl_label = "Done"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        # Does nothing as tool is selected in start operator !!!
        # Update this to "bake" the changes, skip step operation should check if the mesh changed.
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True)
        return self.execute(context)

class NextToolOperator(bpy.types.Operator):
    """Advance to the next tool."""
    bl_idname = "creu.next_tool"
    bl_label = "Next Step"

    def execute(self, context):
        current = context.scene.creu.active_tool

        if current == "IMPORT":
            bpy.ops.creu.start_align()
        elif current == "ALIGN":
            bpy.ops.creu.start_flip_about_xy()
        elif current == "FLIP":
            bpy.ops.creu.start_mesh_quality()
        elif current == "REDUCE":
            bpy.ops.creu.start_erasing()
        elif current == "ERASE":
            bpy.ops.creu.start_hole_filling()
        elif current == "HOLES":
            bpy.ops.creu.start_smooth()
        elif current == "SMOOTH":
            bpy.ops.creu.start_export()

        return {'FINISHED'}

def draw_align_workflow(layout):
    row = layout.row()
    row.label(text = 'Scan Alignment')
    row = layout.row()
    box = row.box()
    row = box.row()
    row.label(text=f"Please select three vertices.")
    row = box.row()

    nvert = 0
    if(len(bpy.context.selected_objects) > 0 and callable(getattr(bpy.context.active_object.data, 'count_selected_items', None))):
        (nvert, _, _) = bpy.context.active_object.data.count_selected_items()
    
    row = box.row()
    row.label(text = f"Selected vertices: {nvert}")
    
    align_enabled = True if nvert == 3 else False
    if(not align_enabled):
        row = box.row()
        row.label(text = f"Please select three vertices to use {AlignToOriginOperator.bl_label}.")

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)
    right.enabled = align_enabled
    right.emboss = 'NORMAL'
    right.operator(AlignToOriginOperator.bl_idname, text = AlignToOriginOperator.bl_label)

    row = layout.row()
    split = row.split(factor=0.5)        
    left = split.column()
    right = split.column()
    right.operator(NextToolOperator.bl_idname, text = NextToolOperator.bl_label)

def draw_flip_workflow(layout):
    row = layout.row()
    row.label(text = 'Flip Mesh')
    row = layout.row()
    box = row.box()
    box.label(text=f"Select an object and then click the {InvertZAxisOperator.bl_label} button to flip the mesh.")

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)
    right.emboss = 'NORMAL'
    right.operator(InvertZAxisOperator.bl_idname, text = InvertZAxisOperator.bl_label)

    row = layout.row()
    split = row.split(factor=0.5)        
    left = split.column()
    right = split.column()
    right.operator(NextToolOperator.bl_idname, text = NextToolOperator.bl_label)

def draw_reduce_workflow(layout):
    row = layout.row()
    row.label(text = 'Standardise Mesh')
    row = layout.row()
    box = row.box()
    box.label(text=f"Use the brush to paint over the mesh to standardise the resolution of the triangles in the mesh.")
    box.label(text=f"Press [ to make the brush smaller.")
    box.label(text=f"Press ] to make the brush larger.")

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)
    right.emboss = 'NORMAL'
    right.operator(NextToolOperator.bl_idname, text = "Next Step")

def draw_import_workflow(layout, context):
    row = layout.row()
    row.label(text = 'Import Mesh')
    row = layout.row()
    
    box = row.box()
    box.label(text="Import an STL")
    box.operator("wm.stl_import", text="Import STL", icon='IMPORT')

    row = layout.row()
    box = row.box()
    box.label(text="Mesh Scaling")

    obj = context.active_object

    if obj is not None:
        box.label(text="Current Dimensions")

        col = box.column(align=True)
        col.enabled = False

        col.prop(obj, "dimensions", text="")

    box.prop(context.scene.creu, "import_scale", text="Scale Factor")
    box.operator(ScaleImportedMeshOperator.bl_idname, text=ScaleImportedMeshOperator.bl_label)

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)
    right.emboss = 'NORMAL'
    right.operator(NextToolOperator.bl_idname, text = "Next Step")

def draw_erase_workflow(layout):
    layout.label(text="Erase Vertices")
    
    box = layout.box()
    box.label(text="Select unwanted geometry and delete it.", icon='INFO')

    # Selection tool
    box.label(text="Selection Tool")
    row = box.row(align=True)
    row.operator(SetBoxSelectOperator.bl_idname, text="", icon='SELECT_SET')
    row.operator(SetCircleSelectOperator.bl_idname, text="", icon='MESH_CIRCLE')
    row.operator(SetLassoSelectOperator.bl_idname, text="", icon='SELECT_DIFFERENCE')

    box.separator()

    # Selection mode
    box.label(text="Selection Mode")
    row = box.row(align=True)
    row.operator(SetSelectionAddOperator.bl_idname, text="Additive", icon='ADD')
    row.operator(SetSelectionSubtractOperator.bl_idname, text="Subtract", icon='REMOVE')

    box.separator()

    # Selection actions
    box.label(text="Selection")

    row = box.row(align=True)

    row.operator(SelectNoneOperator.bl_idname, text="Clear", icon='X')
    box.separator()

    # Delete
    row = box.row()
    row.alert = True

    row.operator(
        DeleteVerticesOperator.bl_idname,
        text="Delete Selected Vertices",
        icon='TRASH'
    )

    layout.separator()

    row = layout.row()
    split = row.split(factor=0.5)

    left = split.column()
    right = split.column()

    left.alert = True

    left.operator(
        CancelOperation.bl_idname,
        text=CancelOperation.bl_label
    )

    right.operator(
        NextToolOperator.bl_idname,
        text="Next Step"
    )

class SetBoxSelectOperator(bpy.types.Operator):
    bl_idname = "creu.box_select"
    bl_label = "Box Select"

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="builtin.select_box")
        return {'FINISHED'}

class SetCircleSelectOperator(bpy.types.Operator):
    bl_idname = "creu.circle_select"
    bl_label = "Circle Select"

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="builtin.select_circle")
        return {'FINISHED'}

class SetLassoSelectOperator(bpy.types.Operator):
    bl_idname = "creu.lasso_select"
    bl_label = "Lasso Select"

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="builtin.select_lasso")
        return {'FINISHED'}

class SetSelectionAddOperator(bpy.types.Operator):
    bl_idname = "creu.add_select"
    bl_label = "Lasso Select"

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="builtin.select_lasso")
        return {'FINISHED'}

class SetSelectionSubtractOperator(bpy.types.Operator):
    bl_idname = "creu.subtract_select"
    bl_label = "Lasso Select"

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="builtin.select_lasso")
        return {'FINISHED'}

class SelectNoneOperator(bpy.types.Operator):
    bl_idname = "creu.delete_vertices"
    bl_label = "Delete Vertices"

    def execute(self, context):
        bpy.ops.mesh.delete(type='VERT')
        return {'FINISHED'}

class DeleteVerticesOperator(bpy.types.Operator):
    bl_idname = "creu.delete_vertices"
    bl_label = "Delete Vertices"

    def execute(self, context):
        bpy.ops.mesh.delete(type='VERT')
        return {'FINISHED'}

def draw_holes_workflow(layout):
    row = layout.row()
    row.label(text = 'Fill Holes')
    row = layout.row()
    box = row.box()

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)
    right.emboss = 'NORMAL'
    right.operator(NextToolOperator.bl_idname, text = "Next Step")

def draw_smooth_workflow(layout):
    row = layout.row()
    row.label(text = 'Smooth Surface')
    row = layout.row()
    box = row.box()

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)
    right.emboss = 'NORMAL'
    right.operator(NextToolOperator.bl_idname, text = "Next Step")

def draw_export_workflow(layout):
    row = layout.row()
    row.label(text = 'Export Mesh')
    row = layout.row()
    box = row.box()

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    right.alert = True
    right.operator(CancelOperation.bl_idname, text = CancelOperation.bl_label)

class CREUAddonPanel(bpy.types.Panel):
    bl_label = "Cushion Processing Tools"
    bl_idname = "CREU_PT_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Cushion Processing"
    #bl_context = "object" # Context will force the addon to appear in the side panel, we want it on the sidebar

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text="Process 3D cushion scans ready for")
        row = layout.row()
        row.label(text="design and manufacturing workflows.")

        TOOLS = [
            (StartImportOperator, 'IMPORT'),
            (StartAlignToOriginOperator, 'ORIENTATION_GLOBAL'),
            (StartInvertZAxisOperator, 'FILE_REFRESH'),
            (StartStandardiseMeshQualityOperator, 'MOD_REMESH'),
            (StartEraseVerticesOperator, 'TRASH'),
            (StartHoleFillingOperator, 'MESH_GRID'),
            (StartSmoothingOperator, 'MOD_SMOOTH'),
            (StartExportOperator, 'EXPORT'),
        ]

        grid = layout.grid_flow(row_major = True, columns = 4)
        for operator, icon in TOOLS:
            grid.operator(
                operator.bl_idname,
                text = "",
                icon = icon
            )

        tool = context.scene.creu.active_tool
        if tool == "IMPORT":
            draw_import_workflow(layout, context)
        elif tool == "ALIGN":
            draw_align_workflow(layout)
        elif tool == "FLIP":
            draw_flip_workflow(layout)
        elif tool == "REDUCE":
            draw_reduce_workflow(layout)
        elif tool == "ERASE":
            draw_erase_workflow(layout)
        elif tool == "HOLES":
            draw_holes_workflow(layout)
        elif tool == "SMOOTH":
            draw_smooth_workflow(layout)
        elif tool == "EXPORT":
            draw_export_workflow(layout)

def register():
    bpy.utils.register_class(SetBoxSelectOperator)
    bpy.utils.register_class(SetCircleSelectOperator)
    bpy.utils.register_class(SetLassoSelectOperator)
    bpy.utils.register_class(SetSelectionAddOperator)
    bpy.utils.register_class(SetSelectionSubtractOperator)
    bpy.utils.register_class(SelectNoneOperator)
    bpy.utils.register_class(DeleteVerticesOperator)

    bpy.utils.register_class(StartImportOperator)
    bpy.utils.register_class(StartAlignToOriginOperator)
    bpy.utils.register_class(StartInvertZAxisOperator)
    bpy.utils.register_class(StartStandardiseMeshQualityOperator)
    bpy.utils.register_class(StartEraseVerticesOperator)
    bpy.utils.register_class(StartHoleFillingOperator)
    bpy.utils.register_class(StartSmoothingOperator)
    bpy.utils.register_class(StartExportOperator)

    bpy.utils.register_class(AlignToOriginOperator)
    bpy.utils.register_class(InvertZAxisOperator)
    bpy.utils.register_class(ScaleImportedMeshOperator)

    bpy.utils.register_class(CancelOperation)
    bpy.utils.register_class(NextToolOperator)

    bpy.utils.register_class(CREUAddonPanel)
    
    bpy.utils.register_class(CREUProperties)
    bpy.types.Scene.creu = bpy.props.PointerProperty(type = CREUProperties)


def unregister():
    bpy.utils.unregister_class(CREUAddonPanel)

    bpy.utils.unregister_class(NextToolOperator)
    bpy.utils.unregister_class(CancelOperation)

    bpy.utils.unregister_class(ScaleImportedMeshOperator)
    bpy.utils.unregister_class(AlignToOriginOperator)
    bpy.utils.unregister_class(InvertZAxisOperator)

    bpy.utils.unregister_class(StartAlignToOriginOperator)
    bpy.utils.unregister_class(StartInvertZAxisOperator)
    bpy.utils.unregister_class(StartStandardiseMeshQualityOperator)
    bpy.utils.unregister_class(StartEraseVerticesOperator)
    bpy.utils.unregister_class(StartHoleFillingOperator)
    bpy.utils.unregister_class(StartSmoothingOperator)
    bpy.utils.unregister_class(StartExportOperator)
    bpy.utils.unregister_class(StartImportOperator)

    bpy.utils.unregister_class(SetBoxSelectOperator)
    bpy.utils.unregister_class(SetCircleSelectOperator)
    bpy.utils.unregister_class(SetLassoSelectOperator)
    bpy.utils.unregister_class(SetSelectionAddOperator)
    bpy.utils.unregister_class(SetSelectionSubtractOperator)
    bpy.utils.unregister_class(SelectNoneOperator)
    bpy.utils.unregister_class(DeleteVerticesOperator)
    
    del bpy.types.Scene.creu
    bpy.utils.unregister_class(CREUProperties)

if __name__ == "__main__":
    register()





















