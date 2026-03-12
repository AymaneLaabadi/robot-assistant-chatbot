import uuid
import gradio as gr
from src.workflow import Workflow

wf = Workflow()


def new_conversation():
    conv = str(uuid.uuid4())
    wf.memory_service.create(conv)
    # return the new conversation id and an empty chat history
    return conv, []


def submit_message(user_text: str, conv_id: str, chat_history: list):
    # Ensure we have a conversation id
    if not conv_id:
        conv_id = str(uuid.uuid4())
        wf.memory_service.create(conv_id)

    # Run through the workflow; it returns the full gradio-history as list of (user, assistant) tuples
    gr_history = wf.run_text(user_text, conversation_id=conv_id)

    # gradio Chatbot expects a list of (user, assistant) tuples; return that
    # Optionally, you could merge with the passed-in chat_history (but we trust memory as source of truth)
    return conv_id, gr_history


with gr.Blocks() as demo:
    gr.Markdown("# Robot Assistant Chatbot — Gradio Test UI")
    with gr.Row():
        conv_id = gr.Textbox(label="Conversation ID (reuse for same chat)", value=str(uuid.uuid4()))
        new_btn = gr.Button("New Conversation")
    chatbot = gr.Chatbot()
    txt = gr.Textbox(placeholder="Enter your message and press Enter", label="Your message")

    new_btn.click(fn=new_conversation, inputs=None, outputs=[conv_id, chatbot])
    txt.submit(fn=submit_message, inputs=[txt, conv_id, chatbot], outputs=[conv_id, chatbot])


def main():
    demo.launch()


if __name__ == "__main__":
    main()