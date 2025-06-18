from string import Template

#### RAG PROMPTS ####

#### System ####
system_prompt = Template("\n".join([
    "You are an assistant to generate a response for the user.",
    "You will be provided by a set of docuemnts associated with the user's query.",
    "You have to generate a response based on the documents provided.",
    "Ignore the documents that are not relevant to the user's query.",
    "You can applogize to the user if you are not able to generate a response.",
    "You have to generate response in the same language as the user's query.",
    "Be polite and respectful to the user.",
    "Be precise and concise in your response. Avoid unnecessary information.",
]))

#### Document ####
document_prompt = Template(
    "\n".join([
        "## Document No: $doc_num",
        "### Content: $chunk_text",
    ])
)

#### Footer ####
footer_prompt = Template("\n".join([
    "Based only on the above documents, please generate an answer for the user.",
    "## Question:",
    "$query",
    "",
    "## Answer:",
]))

# ✅ --- NEW PROMPTS FOR SQL RAG ---


#### SQL Generation ####
sql_generation_prompt = Template("\n".join([
    "Given the following database table schema and a user's question, your task is to generate a single, syntactically correct PostgreSQL SELECT query to answer the question.",
    "IMPORTANT: You MUST ONLY output the raw SQL query. Do not include any explanations, comments, reasoning, backticks, markdown, or any text other than the SQL query itself.",
    "Do not use any tables or columns not listed in the provided schema.",
    "",
    "## Schema:",
    "$schema",
    "",
    "## Question:",
    "$question",
    "",
    "## SQL Query:",
]))


#### Final Answer from SQL Results ####
final_answer_prompt = Template("\n".join([
    "You are a helpful data analyst assistant. A user asked a question, and a SQL query was run against a database to get the following data.",
    "Your task is to formulate a clear, concise, and natural language answer to the user's original question based on the provided data.",
    "If the data is empty or indicates an error, inform the user that the requested information could not be found or there was a problem.",
    "Do not mention that you ran a SQL query. Just provide the answer directly.",
    "",
    "## User's Original Question:",
    "$question",
    "",
    "## Data from Database:",
    "$sql_results",
    "",
    "## Final Answer:",
]))