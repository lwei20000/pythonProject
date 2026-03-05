import streamlit as st
from phi.assistant import Assistant
from phi.document import Document as PhiDocument
from phi.document.reader.pdf import PDFReader
from phi.document.reader.website import WebsiteReader
from phi.utils.log import logger
from assistant import get_groq_assistant  # type: ignore
import sqlalchemy as sa
import pandas as pd

st.set_page_config(
    page_title="Groq RAG",
    page_icon=":orange_heart:",
)
st.title("RAG with Llama3 on Groq")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")

def restart_assistant():
    st.session_state["rag_assistant"] = None
    st.session_state["rag_assistant_run_id"] = None
    if "url_scrape_key" in st.session_state:
        st.session_state["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state:
        st.session_state["file_uploader_key"] += 1
    st.rerun()

def fetch_table_data(connection, table_name):
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, connection)
    return df

def main() -> None:
    # Get LLM model
    llm_model = st.sidebar.selectbox("Select LLM", options=["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"])
    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = llm_model
    elif st.session_state["llm_model"] != llm_model:
        st.session_state["llm_model"] = llm_model
        restart_assistant()

    embeddings_model = st.sidebar.selectbox(
        "Select Embeddings",
        options=["nomic-embed-text", "text-embedding-3-small"],
        help="When you change the embeddings model, the documents will need to be added again.",
    )
    if "embeddings_model" not in st.session_state:
        st.session_state["embeddings_model"] = embeddings_model
    elif st.session_state["embeddings_model"] != embeddings_model:
        st.session_state["embeddings_model"] = embeddings_model
        st.session_state["embeddings_model_updated"] = True
        restart_assistant()

    rag_assistant: Assistant
    if "rag_assistant" not in st.session_state or st.session_state["rag_assistant"] is None:
        logger.info(f"---*--- Creating {llm_model} Assistant ---*---")
        rag_assistant = get_groq_assistant(llm_model=llm_model, embeddings_model=embeddings_model)
        st.session_state["rag_assistant"] = rag_assistant
    else:
        rag_assistant = st.session_state["rag_assistant"]

    # Database connection parameters
    username = "postgres"
    password = "Maran2lunara"
    dbname = "Academix_AI"
    host = "localhost"
    port = 5432

    # Create the database engine
    engine = sa.create_engine(f"postgresql://{username}:{password}@{host}:{port}/{dbname}")

    # Load data from the Postgres database and create documents
    with engine.connect() as connection:
        try:
            result = connection.execute(sa.text("SELECT 1"))
            result.fetchone()
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            st.warning("Could not connect to database")
            return

        tables_to_train = st.multiselect("Select tables to train", options=["staffattendancereport"])

        if st.sidebar.button("Train Database"):
            documents = []
            for table in tables_to_train:
                df = fetch_table_data(connection, f"public.{table}")
                for index, row in df.iterrows():
                    row_json = row.to_json()
                    logger.debug(f"Row JSON: {row_json}")
                    content = f"{table.capitalize()} Report: {row_json}"
                    document = PhiDocument(content=content)
                    try:
                        document.embed(rag_assistant.knowledge_base.vector_db.embedder)
                        documents.append(document)
                        logger.debug(f"Created document: {document.content[:200]}")  # Log the first 200 characters
                    except Exception as e:
                        logger.error(f"Error embedding document: {e}")

            try:
                rag_assistant.knowledge_base.load_documents(documents, upsert=True)
                logger.info("Documents upserted into the knowledge base successfully.")
            except Exception as e:
                logger.error(f"Error upserting documents: {e}")

            st.success("Database training completed.")

    try:
        st.session_state["rag_assistant_run_id"] = rag_assistant.create_run()
    except Exception:
        st.warning("Could not create assistant, is the database running?")
        return

    assistant_chat_history = rag_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Upload a doc and ask me questions..."}]

    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in rag_assistant.run(question):
                response += delta
                resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    if rag_assistant.knowledge_base:
        if "url_scrape_key" not in st.session_state:
            st.session_state["url_scrape_key"] = 0

        input_url = st.sidebar.text_input(
            "Add URL to Knowledge Base", type="default", key=st.session_state["url_scrape_key"]
        )
        add_url_button = st.sidebar.button("Add URL")
        if add_url_button:
            if input_url is not None:
                alert = st.sidebar.info("Processing URLs...", icon="ℹ️")
                if f"{input_url}_scraped" not in st.session_state:
                    scraper = WebsiteReader(max_links=2, max_depth=1)
                    web_documents: List[PhiDocument] = scraper.read(input_url)
                    if web_documents:
                        rag_assistant.knowledge_base.load_documents(web_documents, upsert=True)
                    else:
                        st.sidebar.error("Could not read website")
                    st.session_state[f"{input_url}_uploaded"] = True
                alert.empty()

        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 100

        uploaded_file = st.sidebar.file_uploader(
            "Add a PDF :page_facing_up:", type="pdf", key=st.session_state["file_uploader_key"]
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing PDF...", icon="🧠")
            rag_name = uploaded_file.name.split(".")[0]
            if f"{rag_name}_uploaded" not in st.session_state:
                reader = PDFReader()
                rag_documents: List[PhiDocument] = reader.read(uploaded_file)
                if rag_documents:
                    rag_assistant.knowledge_base.load_documents(rag_documents, upsert=True)
                else:
                    st.sidebar.error("Could not read PDF")
                st.session_state[f"{rag_name}_uploaded"] = True
            alert.empty()

    if rag_assistant.knowledge_base and rag_assistant.knowledge_base.vector_db:
        if st.sidebar.button("Clear Knowledge Base"):
            rag_assistant.knowledge_base.vector_db.clear()
            st.sidebar.success("Knowledge base cleared")

    if rag_assistant.storage:
        rag_assistant_run_ids: List[str] = rag_assistant.storage.get_all_run_ids()
        new_rag_assistant_run_id = st.sidebar.selectbox("Run ID", options=rag_assistant_run_ids)
        if st.session_state["rag_assistant_run_id"] != new_rag_assistant_run_id:
            logger.info(f"---*--- Loading {llm_model} run: {new_rag_assistant_run_id} ---*---")
            st.session_state["rag_assistant"] = get_groq_assistant(
                llm_model=llm_model, embeddings_model=embeddings_model, run_id=new_rag_assistant_run_id
            )
            st.rerun()

    if st.sidebar.button("New Run"):
        restart_assistant()

    if "embeddings_model_updated" in st.session_state:
        st.sidebar.info("Please add documents again as the embeddings model has changed.")
        st.session_state["embeddings_model_updated"] = False

main()
