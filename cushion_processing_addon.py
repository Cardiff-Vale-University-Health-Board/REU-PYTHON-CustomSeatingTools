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

class AlignToOriginOperator(bpy.types.Operator):
    """Aligns an object to the XY plane based on the three currently selected vertices"""
    bl_idname = "object.align_to_origin"
    bl_label = "Align To Origin"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
#        main(context)
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
    bl_idname = "object.flip_about_xy"
    bl_label = "Flip Model"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
#        main(context)
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
        row.label(text="These tools are used to prepare a scanned seat shape for manufacture.", icon='WORLD_DATA')

        box = layout.box()
        row = box.row()
        row.label(text = 'Scan Alignment')
        row = box.row()
    
        nvert = 0
        if(len(context.selected_objects) > 0 and callable(getattr(bpy.context.active_object.data, 'count_selected_items', None))):
            (nvert, _, _) = bpy.context.active_object.data.count_selected_items()
        
        row = box.row()
        row.label(text = f"Selected vertices: {nvert}")
        
        align_enabled = True if nvert == 3 else False
        if(~align_enabled):
            row = box.row()
            row.label(text = f"Please select three vertices to use {AlignToOriginOperator.bl_label}.")
                
        row = box.row()
        row.enabled = align_enabled
        row.operator(AlignToOriginOperator.bl_idname, text = AlignToOriginOperator.bl_label)
                    
        layout.separator()
        box = layout.box()
        row = box.row()
        row.label(text = 'Flip Scan')
        row = box.row()
        row.label(text = 'This operation reverses the z-direction of the model. Effectively rotating the model 180 degrees around the x/y-axes.')
        row = box.row()
        row.operator(InvertZAxisOperator.bl_idname, text = InvertZAxisOperator.bl_label)

def register():
    bpy.utils.register_class(AlignToOriginOperator)
    bpy.utils.register_class(InvertZAxisOperator)
    bpy.utils.register_class(CREUAddonPanel)


def unregister():
    bpy.utils.unregister_class(CREUAddonPanel)
    bpy.utils.unregister_class(InvertZAxisOperator)
    bpy.utils.unregister_class(AlignToOriginOperator)

if __name__ == "__main__":
    register()
