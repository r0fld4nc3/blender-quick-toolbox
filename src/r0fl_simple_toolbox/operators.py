import sys
import bpy
import math
import bmesh
import importlib

from .const import INTERNAL_NAME
from . import utils as u

class SimpleToolbox_OT_ExperimentalOP(bpy.types.Operator):
    bl_label = "Exp Op 1"
    bl_idname = "r0tools.experimental_op_1"
    bl_description = ""
    bl_options = {'REGISTER'}

    def get_viewport(self, context):
        # Get the active 3D viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                # Get the region and region 3D view
                region = None
                rv3d = None
                for r in area.regions:
                    if r.type == 'WINDOW':
                        region = r
                        break
                rv3d = area.spaces[0].region_3d
                
                # Exit the loop once we find a valid viewport
                break
        
        
        # Validate viewport
        if not (region and rv3d):
            self.report({'ERROR'}, "Could not find 3D viewport")
            return (None, None)
        
        return region, rv3d
    
    def get_loose_vertices(self, obj):
        obj_verts = [v.index for v in obj.data.vertices]
        loop_verts = [] # Vertices which are part of a loop
        loose_verts = []

        # bpy.ops.mesh.select_non_manifold() # Requires Edit Mode
        
        for p in obj.data.polygons:
            poly_idx = p.index
            poly_verts = [p.vertices[0], p.vertices[1], p.vertices[2]]
            loop_verts.append(poly_verts)

            print(f"P{poly_idx}: {poly_verts}")
            
        for v in obj_verts:
            found = False
            for vert_loop in loop_verts:
                if v in vert_loop:
                    found = True
                    break

            if not found:
                loose_verts.append(v)

        if loose_verts:
            print(f"{obj.name} has {len(loose_verts)} loose vertices: {loose_verts}")

        return loose_verts

    def execute(self, context):
        print("=== Experimental Operator 1 ===")
        region, rv3d = self.get_viewport(context)

        # Get the actual viewport dimensions
        viewport_width = region.width
        viewport_height = region.height
        viewport_diagonal = math.sqrt(viewport_width**2 + viewport_height**2)

        print(f"Viewport WxH: {viewport_width}x{viewport_height}")

        orig_active = context.view_layer.objects.active
        
        visible_objects = [o for o in u.iter_scene_objects() if o.visible_get()]

        for o in visible_objects:
            self.get_loose_vertices(o)

        context.view_layer.objects.active = orig_active

        return {'FINISHED'}


class SimpleToolbox_OT_ReloadNamedScripts(bpy.types.Operator):
    bl_label = "Reload Script(s)"
    bl_idname = "r0tools.reload_named_scripts"
    bl_description = "Reload only specified scripts from a name text box."
    bl_options = {'REGISTER'}

    def get_input_modules(self) -> list[str]:
        text = bpy.context.scene.r0fl_toolbox_props.reload_modules_prop
        modules = []
        if text:
            modules.extend([t.strip() for t in text.split(',')])
        
        return modules
    
    def reload_module(self, mod_name) -> bool:
        try:
            # Check if the module is already imported
            if mod_name in sys.modules:
                # Reload the module
                module = sys.modules[mod_name]
                importlib.reload(module)
                
                # If it's an addon, re-register its classes
                if hasattr(module, 'register'):
                    try:
                        module.unregister()
                    except Exception as unreg_err:
                        print(f"Error unregistering {mod_name}: {unreg_err}")
                    
                    try:
                        module.register()
                    except Exception as reg_err:
                        print(f"Error re-registering {mod_name}: {reg_err}")
                
                print(f"Reloaded {mod_name}")
                return True
            else:
                print(f"Module {mod_name} not found in sys.modules")
                return False
        except Exception as e:
            print(f"Error reloading {mod_name}: {e}")
            return False

    def execute(self, context):
        modules = self.get_input_modules()

        if not modules:
            modules.append(INTERNAL_NAME)

        failures = []
        successes = []
        if modules:
            for module in modules:
                success = self.reload_module(module)
                if success:
                    successes.append(module)
                else:
                    failures.append(module)
        
        print(f"Reloaded: {successes}")
        print(f"Failed: {failures}")

        reload_msg = f"Reloaded {len(successes)}. Unable to reload {len(failures)}"
        
        try:
            self.report({'INFO'}, reload_msg)
        except Exception as e:
            print(f"Error reporting results: {e}")
        
        u.show_notification(reload_msg)
        
        return {'FINISHED'}
    

class SimpleToolbox_OT_ClearCustomData(bpy.types.Operator):
    bl_label = "Clear Split Normals"
    bl_idname = "r0tools.clear_custom_split_normals"
    bl_description = "Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.\nUseful to quickly clear baked normals/shading assignments of multiple meshes at once."
    bl_options = {'REGISTER', 'UNDO'}
    
    accepted_contexts = ["OBJECT", "EDIT_MESH"]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0
    
    def op_clear_custom_split_normals_data(self, objects):
        """
        Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.
        
        Useful to quickly clear baked normals/shading assignments of multiple meshes at once.
        """
        
        for obj in objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            bpy.ops.object.shade_smooth()
            # bpy.ops.object.shade_smooth() # Not needed. Will give an error if Weighted Normals modifier is present.
            # bpy.context.object.data.use_auto_smooth = True
            # bpy.context.object.data.auto_smooth_angle = 3.14159

    def execute(self, context):
        orig_context = context.mode
        orig_active = bpy.context.view_layer.objects.active

        if context.mode == "EDIT_MESH":
            bpy.ops.object.mode_set(mode="OBJECT")

        objects = [obj for obj in u.iter_scene_objects(selected=True, type="MESH")]
        self.op_clear_custom_split_normals_data(objects)
        bpy.context.view_layer.objects.active = orig_active

        if orig_context != "OBJECT" and orig_context == "EDIT_MESH":
            bpy.ops.object.mode_set(mode='EDIT')

        msg = f"Finished clearing Custom Split Data across {len(objects)} objects"
        # u.show_notification(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class R0TOOLS_update_property_list(bpy.types.Operator):
    bl_idname = "r0tools.update_property_list"
    bl_label = "Update Property List"

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        addon_props = context.scene.r0fl_toolbox_props
        addon_props.custom_property_list.clear()

        unique_props = set()
        for obj in context.selected_objects:
            for prop_name in obj.keys():
                if not prop_name.startswith('_') and prop_name not in unique_props:
                    unique_props.add(prop_name)
                    item = addon_props.custom_property_list.add()
                    item.name = prop_name

        return {'FINISHED'}


class SimpleToolbox_OT_ClearCustomProperties(bpy.types.Operator):
    bl_label = "Delete Custom Properties"
    bl_idname = "r0tools.clear_custom_properties"
    bl_description = "Delete Custom Properties from Object(s)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # FIXME: There has to be a better way to solve this shit...
        if u.continuous_property_list_update not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(u.continuous_property_list_update)

        return len(context.selected_objects) > 0

    def execute(self, context):
        total_deletions = 0
        total_objects = 0
        
        for obj in context.selected_objects:
            # Find selected properties to remove
            props_to_remove = [
                item.name for item in context.scene.r0fl_toolbox_props.custom_property_list 
                if item.selected
            ]
            
            # Remove selected properties
            for prop_name in props_to_remove:
                if prop_name in obj.keys():
                    print(f"Deleting property '{prop_name}' of object {obj.name}")
                    del obj[prop_name]
                    total_deletions += 1
                    total_objects += 1
        
        bpy.ops.r0tools.update_property_list()
        # u.show_notification(f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)")
        self.report({'INFO'}, f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)")
        return {'FINISHED'}

        
class SimpleToolbox_OT_DissolveNthEdge(bpy.types.Operator):
    bl_label = "Remove Nth Edges"
    bl_idname = "r0tools.nth_edges"
    bl_description = "Remove Nth (every other) edges.\n\nUsage: Select 1 edge on each object and run the operation.\nNote: The selected edge and every other edge starting from it will be preserved.\n\nExpand Edges: Per default, the ring selection of edges expands to cover all connected edges to the ring selection. Turning it off will make it so that it only works on the immediate circular ring selection and will not expand to the continuous connected edges."
    bl_options = {'REGISTER', 'UNDO'}

    expand_edges: bpy.props.BoolProperty(name="Expand Edges", default=True)
    keep_initial_selection: bpy.props.BoolProperty(name="Keep Selected Edges", default=True)

    @classmethod
    def poll(cls, context):
        # Ensure at least one object is selected
        return any(obj.type == "MESH" and obj.select_get() for obj in context.selected_objects) and context.mode == "EDIT_MESH"

    def process_object(self, obj, context):
        # Make active
        context.view_layer.objects.active = obj

        if context.mode != "EDIT_MODE":
            bpy.ops.object.mode_set(mode="EDIT")
        
        # Create a bmesh
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.select_mode = {'EDGE'}

        # Currently selected edges
        initial_selection = [edge for edge in bm.edges if edge.select]

        # Edges to delete from all meshes
        edges_delete = []

        for i, edge in enumerate(initial_selection):
            print(f"{i} {edge.index}")
            
            # Deselect all bm edges
            for e in bm.edges:
                e.select = False

            # Select the original edge
            edge.select = True

            # Select the ring and nth
            bpy.ops.mesh.loop_multi_select(ring=True)
            bpy.ops.mesh.select_nth()

            selected_edges = [edge.index for edge in bm.edges if edge.select]
            if edge.index in selected_edges:
                # Deselect all bm edges
                for e in bm.edges:
                    e.select = False
                
                # Select the original edge
                edge.select = True
                bpy.ops.mesh.loop_multi_select(ring=True)
                bpy.ops.mesh.select_nth(offset=1)
            
            if self.expand_edges:
                bpy.ops.mesh.loop_multi_select(ring=False)

            # Store those edges
            edges_delete.extend([edge for edge in bm.edges if edge.select])

            # Deselect initial edge we want to keep
            edge.select = False

        # Make sure to deselect all bm edges too
        for e in bm.edges:
            e.select = False

        for edge in edges_delete:
            edge.select = True
        
        bpy.ops.mesh.dissolve_mode(use_verts=True)

        # Update the mesh
        bmesh.update_edit_mesh(me)
        bm.free()

        # Select initial selection of edges
        if self.keep_initial_selection:
            for edge in initial_selection:
                edge.select = True

    def execute(self, context):
        original_active_obj = context.active_object
        original_mode = context.mode

        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode="OBJECT")

        # Collect selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        # deselect_all()
        for obj in selected_objects:
            # obj.select_set(True)
            self.process_object(obj, context)
            # obj.select_set(False)

        # Return to the original active object and mode
        if original_mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode=original_mode)
        
        # Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_obj

        return {'FINISHED'}
    

class SimpleToolbox_OT_ApplyZenUVTD(bpy.types.Operator):
    bl_label = "Set TD"
    bl_idname = "r0tools.zenuv_set_td"
    bl_description = "Apply Texel Density from ZenUV to objects"
    bl_options = {'REGISTER','UNDO'}

    accepted_contexts = ["OBJECT", "EDIT_MESH"]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0
    
    def execute(self, context):
        context_mode = context.mode
        
        if context_mode not in ["OBJECT", "EDIT_MESH"]:
            self.report({'WARNING'}, "Only performed in Object or Edit modes")
            return {'CANCELLED'}
        
        selected_objs = list(u.iter_scene_objects(selected=True))
        active_obj = bpy.context.view_layer.objects.active
        
        if context_mode == "OBJECT":
            u.deselect_all()
        
        TD = u.get_td_value()
        TD_UNIT = u.get_td_unit()
        
        print(f"Setting TD {TD} for {len(selected_objs)} selected objects with {TD} px/{TD_UNIT}")
        
        bpy.data.scenes["Scene"].zen_uv.td_props.prp_current_td = TD
        bpy.data.scenes["Scene"].zen_uv.td_props.td_unit = TD_UNIT
        bpy.context.scene.zen_uv.td_props.td_set_mode = 'ISLAND'
        
        if context_mode == "OBJECT":
        
            for o in selected_objs:
                try:
                    print(f"Setting {TD} px/{TD_UNIT} for {o.name}")
                    
                    o.select_set(True)
                    
                    bpy.context.view_layer.objects.active = o
                    
                    bpy.context.view_layer.update()
                    
                    # Add a small delay to ensure the selection is registered
                    bpy.app.timers.register(lambda: None, first_interval=0.2)
                    
                    bpy.ops.uv.zenuv_set_texel_density(global_mode=True)
                    
                except Exception as e:
                    print(f"Error: {e}")
                    self.report({'ERROR'}, f"Error: {e}")
                    o.select_set(False)
                    
            for obj in selected_objs:
                obj.select_set(True)
                
            if active_obj:
                bpy.context.view_layer.objects.active = active_obj
        elif context_mode == "EDIT_MESH":
            # Add a small delay to ensure the selection is registered
            bpy.app.timers.register(lambda: None, first_interval=0.2)
            
            bpy.ops.uv.zenuv_set_texel_density(global_mode=True)
        
        # u.show_notification(f"Texel density set to {TD} px/{TD_UNIT} for {len(selected_objs)} objects.")
        self.report({'INFO'}, f"Texel density set to {TD} px/{TD_UNIT} for {len(selected_objs)} objects.")
        
        return {'FINISHED'}


class SimpleToolbox_OT_ClearMeshAttributes(bpy.types.Operator):
    bl_label = "Clear Attributes"
    bl_idname = "r0tools.clear_mesh_attributes"
    bl_description = "Clears unneeded mesh(es) attributes created by various addons.\nPreserves some integral and needed attributes such as material_index that is required for multi-material assignments.\nSometimes certain addons or operations will populate this list with attributes you wish to remove at a later date, be it for parsing or exporting."
    bl_options = {'REGISTER', 'UNDO'}
    
    def op_clear_mesh_attributes(self):
        """
        Clears unneeded mesh(es) attributes created by various addons. Preserves some integral and needed attributes such as material_index that is required for multi-material assignments.
        
        Sometimes certain addons or operations will populate this list with attributes you wish to remove at a later date, be it for parsing or exporting.
        """
        
        print(f"[CLEAR MESH ATTRIBUTES]")
        
        initial_obj = bpy.context.active_object
        
        exclude_filter = ("colorSet", "map", "material_index") # Starts with these tags
        attrs_check = (bpy.types.IntAttribute,
                       bpy.types.FloatAttribute,
                       bpy.types.FloatColorAttribute,
                       bpy.types.StringAttribute,
                       bpy.types.ByteColorAttribute,
                       bpy.types.FloatVectorAttribute,
                       bpy.types.FloatVectorAttributeValue
                       )
        
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                bpy.context.view_layer.objects.active = obj
                mesh = bpy.context.object.data
                print(f"Object: {mesh.name}")
                try:
                    for at in reversed(mesh.attributes.items()):
                        # Check if not T4 Attribute
                        if not isinstance(at[1], attrs_check):
                            continue
                        
                        at_name = at[0]
                        if str(at_name).startswith(exclude_filter):
                            print(f"{' '*2}Keeping Attribute: {at_name}")
                        else:                    
                            print(f"{' '*2}Removing Attribute: {at[0]}")
                            mesh.color_attributes.remove(at[1])
                except Exception as e:
                    print(e)
        
        bpy.context.view_layer.objects.active = initial_obj

    def execute(self, context):
        self.op_clear_mesh_attributes()
        return {'FINISHED'}


class SimpleToolbox_OT_ClearChildrenRecurse(bpy.types.Operator):
    bl_label = "Clear Children"
    bl_idname = "r0tools.clear_all_objects_children"
    bl_description = "For each selected object, clears parenting keeping transform for each child object.\n(SHIFT): Recursively clears parenting for ALL object children and sub-children."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" and obj.select_get() for obj in context.selected_objects) and context.mode == "OBJECT"

    recurse: bpy.props.BoolProperty(default=False)
    
    def op_clear_all_objects_children(self, recurse=False):
        parent_objs = 0
        total_children_cleared = 0
        
        problem_objects = []
        
        active_obj = bpy.context.view_layer.objects.active
        
        # Match selected objects' data names to mesh names
        for o in u.iter_scene_objects(selected=True):
            print(f"Iter {o.name}")
            
            for child in u.iter_children(o, recursive=recurse):
                # print(f"Child: {child.name}")
                try:
                    self.process_child_object(child)
                    total_children_cleared += 1
                except Exception as e:
                    print(f"ERROR: {e}")
                    problem_objects.append(child)
            
            parent_objs += 1
                
        bpy.context.view_layer.objects.active = active_obj
        
        cleared_msg = f"Cleared {total_children_cleared} child objects for {parent_objs} main objects."
        # u.show_notification(cleared_msg)
        self.report({'INFO'}, cleared_msg)
        
        if problem_objects:
            u.deselect_all()
            for obj in problem_objects:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
                    child.hide_set(False)
                    child.hide_viewport = False
            issues_msg = f"The following objects have raised issues: {', '.join([obj.name for obj in problem_objects])}"
            u.show_notification(issues_msg)
            self.report({'WARNING'}, issues_msg)
        
    def process_child_object(self, child):
        """Handle visibility and selection state for a child object"""
        
        was_hidden = child.hide_get()
        was_hidden_viewport = child.hide_viewport
        
        if was_hidden:
            child.hide_set(False)
            
        if was_hidden_viewport:
            child.hide_viewport = False
        
        child.select_set(True)
        bpy.context.view_layer.objects.active = child
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        
        if was_hidden:
            child.hide_set(True)

        if was_hidden_viewport:
            child.hide_viewport = True

    def invoke(self, context, event):
        if event.shift:
            self.recurse = True
        else:
            self.recurse = False

        return self.execute(context)

    def execute(self, context):
        self.op_clear_all_objects_children(recurse=self.recurse)
        return {'FINISHED'}


class SimpleToolbox_OT_ClearAxisSharpEdgesX(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_x"
    bl_description = "Clears sharp edges on the X axis."
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = ["OBJECT", "EDIT_MESH"]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        u.op_clear_sharp_along_axis('X')
        return {'FINISHED'}


class SimpleToolbox_OT_ClearAxisSharpEdgesY(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_y"
    bl_description = "Clears sharp edges on the Y axis."
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = ["OBJECT", "EDIT_MESH"]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        u.op_clear_sharp_along_axis('Y')
        return {'FINISHED'}


class SimpleToolbox_OT_ClearAxisSharpEdgesZ(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_z"
    bl_description = "Clears sharp edges on the Z axis."
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = ["OBJECT", "EDIT_MESH"]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        u.op_clear_sharp_along_axis('Z')
        return {'FINISHED'}


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [
    R0TOOLS_update_property_list, # Useful to register them early
    
    SimpleToolbox_OT_ReloadNamedScripts,
    SimpleToolbox_OT_ClearCustomData,
    SimpleToolbox_OT_ClearCustomProperties,
    SimpleToolbox_OT_ClearMeshAttributes,
    SimpleToolbox_OT_ClearChildrenRecurse,
    SimpleToolbox_OT_ClearAxisSharpEdgesX,
    SimpleToolbox_OT_ClearAxisSharpEdgesY,
    SimpleToolbox_OT_ClearAxisSharpEdgesZ,
    SimpleToolbox_OT_DissolveNthEdge,
    SimpleToolbox_OT_ApplyZenUVTD,
    SimpleToolbox_OT_ExperimentalOP,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    