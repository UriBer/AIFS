#!/usr/bin/env python3
"""
AIFS Lineage Explorer

Provides command-line tools to explore and visualize file lineage in AIFS.
"""

import argparse
import json
import sqlite3
from typing import Dict, List, Set, Optional
from collections import defaultdict, deque
import networkx as nx
import matplotlib.pyplot as plt
from aifs.metadata import MetadataStore


class LineageExplorer:
    """Explore and visualize AIFS lineage relationships."""
    
    def __init__(self, db_path: str):
        """Initialize with metadata store."""
        self.store = MetadataStore(db_path)
        self.db_path = db_path
    
    def get_lineage_graph(self) -> nx.DiGraph:
        """Build a NetworkX graph of all lineage relationships."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all lineage relationships
        cursor.execute("""
            SELECT child_id, parent_id, transform_name, transform_digest, created_at
            FROM lineage
            ORDER BY created_at
        """)
        
        G = nx.DiGraph()
        
        for child_id, parent_id, transform_name, transform_digest, created_at in cursor.fetchall():
            G.add_edge(
                parent_id, 
                child_id,
                transform_name=transform_name or "unknown",
                transform_digest=transform_digest or "",
                created_at=created_at
            )
        
        conn.close()
        return G
    
    def find_ancestors(self, asset_id: str, max_depth: int = 10) -> List[Dict]:
        """Find all ancestors of an asset."""
        G = self.get_lineage_graph()
        
        if asset_id not in G:
            return []
        
        ancestors = []
        visited = set()
        queue = deque([(asset_id, 0)])
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_depth or current_id in visited:
                continue
                
            visited.add(current_id)
            
            # Get predecessors (parents)
            for parent_id in G.predecessors(current_id):
                if parent_id not in visited:
                    edge_data = G[parent_id][current_id]
                    ancestors.append({
                        "asset_id": parent_id,
                        "child_id": current_id,
                        "transform_name": edge_data.get("transform_name", "unknown"),
                        "transform_digest": edge_data.get("transform_digest", ""),
                        "created_at": edge_data.get("created_at", ""),
                        "depth": depth + 1
                    })
                    queue.append((parent_id, depth + 1))
        
        return ancestors
    
    def find_descendants(self, asset_id: str, max_depth: int = 10) -> List[Dict]:
        """Find all descendants of an asset."""
        G = self.get_lineage_graph()
        
        if asset_id not in G:
            return []
        
        descendants = []
        visited = set()
        queue = deque([(asset_id, 0)])
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_depth or current_id in visited:
                continue
                
            visited.add(current_id)
            
            # Get successors (children)
            for child_id in G.successors(current_id):
                if child_id not in visited:
                    edge_data = G[current_id][child_id]
                    descendants.append({
                        "parent_id": current_id,
                        "asset_id": child_id,
                        "transform_name": edge_data.get("transform_name", "unknown"),
                        "transform_digest": edge_data.get("transform_digest", ""),
                        "created_at": edge_data.get("created_at", ""),
                        "depth": depth + 1
                    })
                    queue.append((child_id, depth + 1))
        
        return descendants
    
    def get_lineage_path(self, from_asset: str, to_asset: str) -> Optional[List[str]]:
        """Find the shortest lineage path between two assets."""
        G = self.get_lineage_graph()
        
        if from_asset not in G or to_asset not in G:
            return None
        
        try:
            path = nx.shortest_path(G, from_asset, to_asset)
            return path
        except nx.NetworkXNoPath:
            return None
    
    def visualize_lineage(self, asset_id: str, max_depth: int = 3, output_file: str = None):
        """Create a visual representation of lineage around an asset."""
        G = self.get_lineage_graph()
        
        if asset_id not in G:
            print(f"Asset {asset_id} not found in lineage graph")
            return
        
        # Get subgraph around the asset
        subgraph_nodes = set([asset_id])
        
        # Add ancestors and descendants up to max_depth
        for depth in range(max_depth):
            new_nodes = set()
            for node in subgraph_nodes:
                new_nodes.update(G.predecessors(node))
                new_nodes.update(G.successors(node))
            subgraph_nodes.update(new_nodes)
        
        subgraph = G.subgraph(subgraph_nodes)
        
        # Create visualization
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(subgraph, k=2, iterations=50)
        
        # Color the target asset differently
        node_colors = ['red' if node == asset_id else 'lightblue' for node in subgraph.nodes()]
        
        nx.draw(subgraph, pos, 
                node_color=node_colors,
                node_size=1000,
                font_size=8,
                font_weight='bold',
                arrows=True,
                arrowsize=20,
                edge_color='gray',
                with_labels=True)
        
        # Add edge labels for transforms
        edge_labels = {}
        for (u, v, d) in subgraph.edges(data=True):
            edge_labels[(u, v)] = d.get('transform_name', '')[:10]  # Truncate long names
        
        nx.draw_networkx_edge_labels(subgraph, pos, edge_labels, font_size=6)
        
        plt.title(f"Lineage Graph for Asset {asset_id[:8]}...")
        plt.axis('off')
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Lineage graph saved to {output_file}")
        else:
            plt.show()
    
    def export_lineage_json(self, asset_id: str = None, output_file: str = "lineage.json"):
        """Export lineage data as JSON."""
        if asset_id:
            # Export lineage for specific asset
            ancestors = self.find_ancestors(asset_id)
            descendants = self.find_descendants(asset_id)
            
            data = {
                "asset_id": asset_id,
                "ancestors": ancestors,
                "descendants": descendants,
                "total_ancestors": len(ancestors),
                "total_descendants": len(descendants)
            }
        else:
            # Export all lineage data
            G = self.get_lineage_graph()
            data = {
                "total_assets": G.number_of_nodes(),
                "total_relationships": G.number_of_edges(),
                "relationships": []
            }
            
            for (u, v, d) in G.edges(data=True):
                data["relationships"].append({
                    "parent_id": u,
                    "child_id": v,
                    "transform_name": d.get("transform_name", ""),
                    "transform_digest": d.get("transform_digest", ""),
                    "created_at": d.get("created_at", "")
                })
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Lineage data exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="AIFS Lineage Explorer")
    parser.add_argument("--db", default="~/.aifs/aifs.db", help="Path to AIFS database")
    parser.add_argument("--asset", help="Asset ID to explore")
    parser.add_argument("--ancestors", action="store_true", help="Show ancestors")
    parser.add_argument("--descendants", action="store_true", help="Show descendants")
    parser.add_argument("--path", help="Find path between two assets (format: from_asset_id,to_asset_id)")
    parser.add_argument("--visualize", action="store_true", help="Create lineage visualization")
    parser.add_argument("--export", help="Export lineage data to JSON file")
    parser.add_argument("--max-depth", type=int, default=10, help="Maximum depth for lineage search")
    
    args = parser.parse_args()
    
    # Expand user directory
    import os
    db_path = os.path.expanduser(args.db)
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    explorer = LineageExplorer(db_path)
    
    if args.asset:
        print(f"Exploring lineage for asset: {args.asset}")
        
        if args.ancestors:
            print("\n=== ANCESTORS ===")
            ancestors = explorer.find_ancestors(args.asset, args.max_depth)
            for ancestor in ancestors:
                print(f"  {ancestor['depth']} levels up: {ancestor['asset_id'][:8]}... "
                      f"(via {ancestor['transform_name']})")
        
        if args.descendants:
            print("\n=== DESCENDANTS ===")
            descendants = explorer.find_descendants(args.asset, args.max_depth)
            for descendant in descendants:
                print(f"  {descendant['depth']} levels down: {descendant['asset_id'][:8]}... "
                      f"(via {descendant['transform_name']})")
        
        if args.visualize:
            print("\n=== CREATING VISUALIZATION ===")
            explorer.visualize_lineage(args.asset, max_depth=3)
    
    if args.path:
        from_asset, to_asset = args.path.split(',')
        print(f"Finding path from {from_asset} to {to_asset}")
        path = explorer.get_lineage_path(from_asset, to_asset)
        if path:
            print(f"Path: {' -> '.join([p[:8] + '...' for p in path])}")
        else:
            print("No path found")
    
    if args.export:
        print(f"Exporting lineage data to {args.export}")
        explorer.export_lineage_json(args.asset, args.export)


if __name__ == "__main__":
    main()
