import chainlit as cl
from emmy_core import get_emmy_brain

@cl.on_chat_start
async def on_chat_start():
    # Load agent pas user buka browser
    cl.user_session.set("agent", get_emmy_brain())
    await cl.Message(content="Hello Darling! I'm ready via Web UI now. ❤️").send()

@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    
    # Chainlit punya session id unik per tab browser
    thread_id = f"chainlit_{cl.user_session.get('id')}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Panggil Otak
    response = await cl.make_async(agent.invoke)(
        {"messages": [{"role": "user", "content": message.content}]},
        config
    )
    
    bot_reply = response['messages'][-1].content
    # TAMBAHIN PARAMETER author="Emmy"
    await cl.Message(
        content=bot_reply, 
        author="Emmy"  # <--- INI KUNCINYA!
    ).send()