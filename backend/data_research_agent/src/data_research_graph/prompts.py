report_planner_query_writer_instructions = """You are performing research for a report with a focus on gathering both comprehensive information and numerical data.

<Report topic>
{topic}
</Report topic>

<Report organization>
{report_organization}
</Report organization>

<Task>
Your goal is to generate {number_of_queries} web search queries that will help gather information for planning the report sections. This includes both legacy report content and numerical data related to the topic.

**For Report Planning Content:**
- General information to understand the topic scope
- Background context and expert analysis
- Information that satisfies the report organization requirements

**For Numerical Data Search:**
Focus specifically on finding:
- Statistical data, metrics, and quantitative measurements
- Financial figures, market data, and performance indicators
- Survey results, research findings, and numerical studies
- Trend data, growth rates, and comparative numbers
- Industry benchmarks and numerical comparisons

The queries should:

1. Be related to the Report topic
2. Help satisfy the requirements specified in the report organization
3. Target both descriptive content and specific numerical/statistical data
4. Look for authoritative sources with credible data and statistics
5. Focus on recent, reliable numerical information and comprehensive topic coverage

Make the queries specific enough to find high-quality, relevant sources that provide both the breadth needed for the report structure and the numerical data to support quantitative analysis.
</Task>

<Format>
Call the Queries tool
</Format>
"""

report_planner_instructions = """I want a plan for a report that is concise and focused.

<Report topic>
The topic of the report is:
{topic}
</Report topic>

<Report organization>
The report should follow this organization: 
{report_organization}
</Report organization>

<Context>
Here is context to use to plan the sections of the report: 
{context}
</Context>

<Task>
Generate a list of sections for the report. Your plan should be tight and focused with NO overlapping sections or unnecessary filler. 

For example, a good report structure might look like:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ financial analysis of A and B
6/ conclusion

Each section should have the fields:

- Name - Name for this section of the report.
- Description - Brief overview of the main topics covered in this section.
- Research - Whether to perform web research for this section of the report.
- Content - The content of the section, which you will leave blank for now.

Integration guidelines:
- Include examples and implementation details within main topic sections, not as separate sections
- Ensure each section has a distinct purpose with no content overlap
- Combine related concepts rather than separating them
- For company/stock topics, always include a financial analysis section

Before submitting, review your structure to ensure it has no redundant sections and follows a logical flow.
</Task>

<Feedback>
Here is feedback on the report structure from review (if any):
{feedback}
</Feedback>

<Format>
Call the Sections tool 
</Format>
"""

query_writer_instructions = """You are an expert technical writer crafting targeted web search queries that will gather comprehensive information for writing a technical report section.

<Report topic>
{topic}
</Report topic>

<Section topic>
{section_topic}
</Section topic>

<Task>
Your goal is to generate {number_of_queries} search queries that will help gather comprehensive information above the section topic. 

The queries should:

1. Be related to the topic 
2. Examine different aspects of the topic

Make the queries specific enough to find high-quality, relevant sources.
</Task>

<Format>
Call the Queries tool 
</Format>
"""


ticker_writer_instructions = """You are a financial expert tasked with finding the stock ticker symbol for a company.

<Report topic>
{topic}
</Report topic>

<Task>
Your task is simple:
1. If the topic mentions a specific company, return ONLY its ticker symbol
2. If no specific company is mentioned, return an empty string

Example outputs:
- "AAPL" (for Apple)
- "TSLA" (for Tesla)
- "GOOGL" (for Alphabet Class A)
- "" (empty string if no company mentioned)
</Task>

<Format>
Return ONLY the ticker symbol, nothing else.
</Format>
"""

section_writer_instructions = """Write one section of a research report.

<Task>
1. Review the report topic, section name, and section topic carefully.
2. If present, review any existing section content. 
3. Then, look at the provided Source material.
4. Decide the sources that you will use it to write a report section.
5. Write the report section and list your sources.
6. You should add numerical data tables when relevant data is available in the source material to enhance the section with quantitative information.
</Task>

<Writing Guidelines>
- If existing section content is not populated, write from scratch
- If existing section content is populated, synthesize it with the source material
- Strict 150-200 word limit except for numerical data tables
- Use simple, clear language
- Use short paragraphs (2-3 sentences max)
- Use ## for section title (Markdown format)
- Add numerical data tables using proper Markdown table format when relevant statistical, financial, or quantitative data is available in the source material
</Writing Guidelines>

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
</Final Check>
"""

section_writer_inputs = """ 
<Report topic>
{topic}
</Report topic>

<Section name>
{section_name}
</Section name>

<Section topic>
{section_topic}
</Section topic>

<Existing section content (if populated)>
{section_content}
</Existing section content>

<Source material>
{context}
</Source material>

<API Data (if available)>
{api_data}
</API Data>
"""

section_grader_instructions = """Review a report section relative to the specified topic:

<Report topic>
{topic}
</Report topic>

<section topic>
{section_topic}
</section topic>

<section content>
{section}
</section content>

<task>
Evaluate whether the section content adequately addresses the section topic.

If the section content does not adequately address the section topic, generate {number_of_follow_up_queries} follow-up search queries to gather missing information.
</task>

<format>
Call the Feedback tool and output with the following schema:

grade: Literal["pass","fail"] = Field(
    description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
)
follow_up_queries: List[SearchQuery] = Field(
    description="List of follow-up search queries.",
)
</format>
"""

final_section_writer_instructions = """You are an expert technical writer crafting a section that synthesizes information from the rest of the report.

<Report topic>
{topic}
</Report topic>

<Section name>
{section_name}
</Section name>

<Section topic> 
{section_topic}
</Section topic>

<Available report content>
{context}
</Available report content>

<Task>
1. Section-Specific Approach:

For Introduction:
- Use # for report title (Markdown format)
- 50-100 word limit
- Write in simple and clear language
- Focus on the core motivation for the report in 1-2 paragraphs
- Use a clear narrative arc to introduce the report
- Include NO structural elements (no lists or tables)
- No sources section needed

For Conclusion/Summary:
- Use ## for section title (Markdown format)
- 100-150 word limit
- For comparative reports:
    * Must include a focused comparison table using Markdown table syntax
    * Table should distill insights from the report
    * Keep table entries clear and concise
- For non-comparative reports: 
    * Only use ONE structural element IF it helps distill the points made in the report:
    * Either a focused table comparing items present in the report (using Markdown table syntax)
    * Or a short list using proper Markdown list syntax:
      - Use `*` or `-` for unordered lists
      - Use `1.` for ordered lists
      - Ensure proper indentation and spacing
- End with specific next steps or implications
- No sources section needed

3. Writing Approach:
- Use concrete details over general statements
- Make every word count
- Focus on your single most important point
</Task>

<Quality Checks>
- For introduction: 50-100 word limit, # for report title, no structural elements, no sources section
- For conclusion: 100-150 word limit, ## for section title, only ONE structural element at most, no sources section
- Markdown format
- Do not include word count or any preamble in your response
</Quality Checks>"""

financial_section_writer_instructions = """You are a financial data formatter. Your job is to copy and paste ALL the provided financial data tables EXACTLY as they appear, without any changes or summarization.

<Task>
COPY EVERY TABLE AND TEXT from the Available Data section below EXACTLY as provided. Do not summarize, modify, or interpret anything.

IMPORTANT: Copy the complete tables - do not truncate or shorten them. If a table has 20 rows, copy all 20 rows.
</Task>

<Writing Guidelines>
- Copy ALL provided data tables character-for-character
- Keep ALL table rows, columns, and formatting exactly the same
- Include ALL explanatory text and notes as provided
- Use ## for the main section title: ## Financial Data for {ticker}
- Copy the ### subsection titles exactly as provided
- Do NOT add any analysis, commentary, or interpretation
- Do NOT summarize or truncate any tables
</Writing Guidelines>

<Available Data>
Topic: {topic}
Section Topic: {section_topic}
Company Ticker: {ticker}

### Stock Price History
{price_data_rows}

### Close Price Predictions (Next 15 Trading Days)  
{predicted_price_rows}

### Revenue & Net Income
{income_statements_section}

### Leverage & Capital Efficiency
{balance_sheets_section}

### Cash Flow
{cash_flow_section}

### Insider Share Ownership
{insider_trades_section}

</Available Data>

<EXACT OUTPUT FORMAT>
Start your response with:

## Financial Data for {ticker}

Then copy EVERY line from the Available Data section above, starting with:

### Stock Price History
[Copy the exact price_data_rows table here]

### Close Price Predictions (Next 15 Trading Days)
[Copy the exact predicted_price_rows table here]

### Revenue & Net Income
[Copy the exact income_statements_section content here]

### Leverage & Capital Efficiency
[Copy the exact balance_sheets_section content here]

### Cash Flow
[Copy the exact cash_flow_section content here]

### Insider Share Ownership
[Copy the exact insider_trades_section content here]

</EXACT OUTPUT FORMAT>

<CRITICAL INSTRUCTION>
You MUST copy every single table row and every piece of text exactly as provided. Do not skip any rows. Do not summarize. Do not add "..." or truncation. Copy everything completely.
</CRITICAL INSTRUCTION>
"""
