"""Mesh tools for COMSOL MCP Server."""

from typing import Optional
from mcp.server.fastmcp import FastMCP

from .session import session_manager


def register_mesh_tools(mcp: FastMCP) -> None:
    """Register mesh tools with the MCP server."""
    
    @mcp.tool()
    def mesh_list(model_name: Optional[str] = None) -> dict:
        """
        List all mesh sequences in a model.
        
        Args:
            model_name: Model name (default: current model)
        
        Returns:
            List of mesh sequence names
        """
        model = session_manager.get_model(model_name)
        if model is None:
            return {
                "success": False,
                "error": f"Model not found: {model_name or 'no current model'}"
            }
        
        try:
            meshes = model.meshes()
            return {
                "success": True,
                "meshes": meshes,
                "count": len(meshes),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list meshes: {str(e)}"}
    
    @mcp.tool()
    def mesh_create(
        mesh_name: str = "mesh1",
        geometry_name: Optional[str] = None,
        mesh_size: int = 5,
        model_name: Optional[str] = None
    ) -> dict:
        """
        Create (or re-run) a mesh sequence and generate the mesh.

        Creates the mesh sequence if it doesn't exist and runs the mesher.

        Args:
            mesh_name: Mesh sequence name (default: "mesh1")
            geometry_name: Geometry to mesh (default: first geometry)
            mesh_size: Mesh element size 1=fine ... 9=coarse (default: 5)
            model_name: Model name (default: current model)

        Returns:
            Mesh generation status
        """
        model = session_manager.get_model(model_name)
        if model is None:
            return {
                "success": False,
                "error": f"Model not found: {model_name or 'no current model'}"
            }

        try:
            jm = model.java

            # Find the first component
            comp = None
            for c in jm.component():
                comp = c
                break
            if comp is None:
                return {"success": False, "error": "No component found. Create one first with model_create_component."}

            # Find geometry
            geoms = list(comp.geom())
            if not geoms:
                return {"success": False, "error": "No geometry found. Create geometry first."}

            target_geom = geometry_name or geoms[0].tag()

            # Create or get mesh
            existing = list(comp.mesh())
            mesh = None
            for m in existing:
                if m.tag() == mesh_name:
                    mesh = m
                    break

            if mesh is None:
                mesh = comp.mesh().create(mesh_name, target_geom)

            mesh.autoMeshSize(mesh_size)
            mesh.run()

            return {
                "success": True,
                "mesh": mesh_name,
                "geometry": target_geom,
                "size": mesh_size,
                "message": f"Mesh '{mesh_name}' on geometry '{target_geom}' generated (size={mesh_size}).",
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create mesh: {str(e)}"}
    
    @mcp.tool()
    def mesh_info(
        mesh_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> dict:
        """
        Get information about a mesh.
        
        Args:
            mesh_name: Mesh sequence name (default: first mesh)
            model_name: Model name (default: current model)
        
        Returns:
            Mesh statistics including element counts
        """
        model = session_manager.get_model(model_name)
        if model is None:
            return {
                "success": False,
                "error": f"Model not found: {model_name or 'no current model'}"
            }
        
        try:
            meshes = model.meshes()
            if not meshes:
                return {"success": False, "error": "No meshes defined in model."}
            
            target = mesh_name or meshes[0]
            if target not in meshes:
                return {"success": False, "error": f"Mesh not found: {target}"}
            
            mesh_node = model / "meshes" / target
            
            info = {
                "name": target,
            }
            
            try:
                java_mesh = mesh_node.java
                if hasattr(java_mesh, 'getVertex'):
                    info["num_vertices"] = java_mesh.getVertex().size()
                if hasattr(java_mesh, 'getElement'):
                    info["num_elements"] = java_mesh.getElement().size()
            except Exception:
                pass
            
            try:
                children = [child.name() for child in mesh_node.children()]
                info["features"] = children
            except Exception:
                pass
            
            return {
                "success": True,
                "mesh": info,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get mesh info: {str(e)}"}
