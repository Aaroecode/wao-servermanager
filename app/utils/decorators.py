class MCWebhookEvent:
    def __init__(self):
        self.mc_webhooks = {}
        self.custom_webhooks = {}
        self.commands = {}
    

    def mc_webhook(self, event_name):
        def decorator(func):
            self.mc_webhooks[event_name] = func
            print(func.__name__, "webhook event registered")
            return func
        return decorator
    
    def custom_webhook(self, event_name):
        def decorator(func):
            self.custom_webhooks[event_name] = func
            return func
        return decorator
    
    async def call_event(self, data):
        event_name = data.get("event")
        print(event_name)
        if event_name in self.mc_webhooks:
            await self.mc_webhooks[event_name](data)
        else:
            await self.custom_webhooks[event_name](data)
    
    def command_event(self, command_name):
        def decorator(func):
            self.commands[func.__name__] = func
            print(func.__name__, "command event registered")
            return func
        return decorator
    
    async def call_command(self, data):
        command_name = data.get("command").split()[0]
        command_name = command_name.lstrip("/")
        if command_name in self.commands:
            await self.commands[command_name](data)
        


event_handler = MCWebhookEvent()