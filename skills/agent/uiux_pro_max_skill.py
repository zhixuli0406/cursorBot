"""
UI/UX Pro Max Agent Skill for CursorBot

Provides design intelligence for building professional UI/UX:
- 67 UI Styles (Glassmorphism, Minimalism, Brutalism, etc.)
- 96 Color Palettes (SaaS, E-commerce, Healthcare, etc.)
- 57 Font Pairings (curated typography combinations)
- 100 Industry-Specific Reasoning Rules
- Complete Design System Generation

Based on: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
"""

import os
import sys
from pathlib import Path

from src.core.skills import AgentSkill, AgentSkillInfo

# Add the ui-ux-pro-max scripts to path
UIUX_BASE = Path(__file__).parent / "ui-ux-pro-max"
UIUX_SCRIPTS = UIUX_BASE / "cli" / "assets" / "scripts"
UIUX_DATA = UIUX_BASE / "cli" / "assets" / "data"

# Patch the DATA_DIR in core.py dynamically
if UIUX_SCRIPTS.exists():
    sys.path.insert(0, str(UIUX_SCRIPTS))


class UIUXDesignSystemSkill(AgentSkill):
    """
    Generate complete design system recommendations.
    
    Uses AI-powered reasoning to recommend:
    - Landing page patterns
    - UI styles
    - Color palettes
    - Typography pairings
    - Key effects and anti-patterns
    """
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="uiux_design_system",
            description="Generate complete UI/UX design system recommendations for any project type",
            version="2.0.0",
            author="nextlevelbuilder",
            parameters={
                "query": "Project description (e.g., 'SaaS dashboard', 'e-commerce luxury')",
                "project_name": "Optional project name",
                "output_format": "Output format: 'ascii' (default) or 'markdown'",
            },
            examples=[
                "Generate design system for a beauty spa website",
                "Create UI/UX guidelines for a fintech banking app",
                "Design system for a SaaS dashboard",
            ],
            categories=["design", "ui", "ux", "style"],
        )
    
    async def execute(self, **kwargs) -> dict:
        query = kwargs.get("query", "")
        if not query:
            return {"error": "Please provide a project description (query)"}
        
        project_name = kwargs.get("project_name", query.title())
        output_format = kwargs.get("output_format", "markdown")
        
        try:
            # Dynamically import and patch
            import importlib.util
            
            # Load core module with patched DATA_DIR
            core_path = UIUX_SCRIPTS / "core.py"
            if not core_path.exists():
                return {"error": f"UI/UX Pro Max not found. Please install it first."}
            
            spec = importlib.util.spec_from_file_location("uiux_core", core_path)
            core_module = importlib.util.module_from_spec(spec)
            
            # Patch DATA_DIR before loading
            core_module.DATA_DIR = UIUX_DATA
            spec.loader.exec_module(core_module)
            
            # Load design_system module
            ds_path = UIUX_SCRIPTS / "design_system.py"
            ds_spec = importlib.util.spec_from_file_location("uiux_design_system", ds_path)
            ds_module = importlib.util.module_from_spec(ds_spec)
            
            # Inject core module
            ds_module.DATA_DIR = UIUX_DATA
            sys.modules["core"] = core_module
            ds_spec.loader.exec_module(ds_module)
            
            # Generate design system
            result = ds_module.generate_design_system(
                query=query,
                project_name=project_name,
                output_format=output_format,
            )
            
            return {
                "status": "success",
                "project": project_name,
                "query": query,
                "design_system": result,
            }
            
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


class UIUXStyleSearchSkill(AgentSkill):
    """
    Search UI styles, colors, typography, and more.
    """
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="uiux_search",
            description="Search UI/UX styles, color palettes, typography, charts, and guidelines",
            version="2.0.0",
            author="nextlevelbuilder",
            parameters={
                "query": "Search query (e.g., 'glassmorphism', 'dashboard colors')",
                "domain": "Search domain: style, color, chart, landing, product, ux, typography, icons",
                "max_results": "Maximum results to return (default: 3)",
            },
            examples=[
                "Search for glassmorphism style",
                "Find color palette for fintech",
                "Search typography for luxury brands",
            ],
            categories=["design", "search", "ui", "ux"],
        )
    
    async def execute(self, **kwargs) -> dict:
        query = kwargs.get("query", "")
        if not query:
            return {"error": "Please provide a search query"}
        
        domain = kwargs.get("domain")
        max_results = int(kwargs.get("max_results", 3))
        
        try:
            import importlib.util
            
            # Load core module with patched DATA_DIR
            core_path = UIUX_SCRIPTS / "core.py"
            if not core_path.exists():
                return {"error": f"UI/UX Pro Max not found at {core_path}"}
            
            spec = importlib.util.spec_from_file_location("uiux_core", core_path)
            core_module = importlib.util.module_from_spec(spec)
            core_module.DATA_DIR = UIUX_DATA
            spec.loader.exec_module(core_module)
            
            # Perform search
            result = core_module.search(query, domain, max_results)
            
            return {
                "status": "success",
                "query": query,
                "domain": result.get("domain", domain),
                "count": result.get("count", 0),
                "results": result.get("results", []),
            }
            
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


class UIUXStackGuidelinesSkill(AgentSkill):
    """
    Get stack-specific UI/UX guidelines.
    """
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="uiux_stack",
            description="Get UI/UX guidelines for specific tech stacks (React, Vue, Tailwind, etc.)",
            version="2.0.0",
            author="nextlevelbuilder",
            parameters={
                "query": "What you're looking for (e.g., 'form validation', 'responsive layout')",
                "stack": "Tech stack: html-tailwind, react, nextjs, vue, nuxtjs, svelte, swiftui, flutter, react-native, shadcn, jetpack-compose",
            },
            examples=[
                "Get React performance guidelines",
                "Tailwind form best practices",
                "Next.js responsive layout tips",
            ],
            categories=["design", "code", "stack", "guidelines"],
        )
    
    async def execute(self, **kwargs) -> dict:
        query = kwargs.get("query", "")
        stack = kwargs.get("stack", "html-tailwind")
        
        if not query:
            return {"error": "Please provide a search query"}
        
        try:
            import importlib.util
            
            # Load core module
            core_path = UIUX_SCRIPTS / "core.py"
            if not core_path.exists():
                return {"error": f"UI/UX Pro Max not found"}
            
            spec = importlib.util.spec_from_file_location("uiux_core", core_path)
            core_module = importlib.util.module_from_spec(spec)
            core_module.DATA_DIR = UIUX_DATA
            spec.loader.exec_module(core_module)
            
            # Check valid stack
            available_stacks = core_module.AVAILABLE_STACKS
            if stack not in available_stacks:
                return {
                    "error": f"Unknown stack: {stack}",
                    "available_stacks": available_stacks,
                }
            
            # Perform stack search
            result = core_module.search_stack(query, stack, max_results=5)
            
            return {
                "status": "success",
                "query": query,
                "stack": stack,
                "count": result.get("count", 0),
                "results": result.get("results", []),
            }
            
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


class UIUXQuickReferenceSkill(AgentSkill):
    """
    Get quick UI/UX reference and checklists.
    """
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="uiux_checklist",
            description="Get UI/UX pre-delivery checklist and quick reference",
            version="2.0.0",
            author="nextlevelbuilder",
            parameters={
                "type": "Checklist type: 'pre-delivery', 'accessibility', 'performance', 'all'",
            },
            examples=[
                "Get pre-delivery UI checklist",
                "Show accessibility guidelines",
                "Performance checklist for UI",
            ],
            categories=["design", "checklist", "ui", "ux"],
        )
    
    async def execute(self, **kwargs) -> dict:
        checklist_type = kwargs.get("type", "all")
        
        checklists = {
            "pre-delivery": {
                "name": "Pre-Delivery Checklist",
                "items": [
                    "No emojis as icons (use SVG: Heroicons/Lucide)",
                    "cursor-pointer on all clickable elements",
                    "Hover states with smooth transitions (150-300ms)",
                    "Light mode: text contrast 4.5:1 minimum",
                    "Focus states visible for keyboard navigation",
                    "prefers-reduced-motion respected",
                    "Responsive: 375px, 768px, 1024px, 1440px",
                    "No content hidden behind fixed navbars",
                    "No horizontal scroll on mobile",
                ],
            },
            "accessibility": {
                "name": "Accessibility Checklist",
                "items": [
                    "All images have alt text",
                    "Form inputs have associated labels",
                    "Color is not the only means of conveying information",
                    "Interactive elements are keyboard accessible",
                    "ARIA attributes used correctly",
                    "Skip links for main content",
                    "Proper heading hierarchy (h1-h6)",
                    "Focus order follows visual order",
                ],
            },
            "performance": {
                "name": "Performance Checklist",
                "items": [
                    "Images optimized and lazy loaded",
                    "Critical CSS inlined",
                    "Fonts preloaded or system fonts used",
                    "No layout shift (CLS < 0.1)",
                    "First Input Delay < 100ms",
                    "Bundle size minimized",
                    "Code splitting for routes",
                    "Caching headers configured",
                ],
            },
        }
        
        if checklist_type == "all":
            return {
                "status": "success",
                "checklists": checklists,
            }
        elif checklist_type in checklists:
            return {
                "status": "success",
                "checklist": checklists[checklist_type],
            }
        else:
            return {
                "error": f"Unknown checklist type: {checklist_type}",
                "available_types": list(checklists.keys()) + ["all"],
            }
