def register_skills(registry):
    """Example plugin skill."""
    class HelloWorldSkill:
        async def execute(self, params):
            print("Hello from the plugin system!")
            return {"status": "success", "message": "Hello World"}

    registry.register("hello_world", HelloWorldSkill())
