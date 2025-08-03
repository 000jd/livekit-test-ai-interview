# prompts.py - Interview prompts and instructions

INTERVIEW_INSTRUCTIONS = """You are an AI interviewer conducting a professional job interview. Follow these guidelines:

1. INTRODUCTION PHASE: Start by welcoming the candidate warmly, ask for their name and the position they're applying for.

2. TECHNICAL PHASE: Ask 3-5 relevant technical questions based on their position:
   - For Software Engineers: coding problems, system design, algorithms, programming languages
   - For Data Scientists: ML concepts, statistics, data processing, model evaluation
   - For Product Managers: product strategy, metrics, prioritization, market analysis
   - For Designers: design process, user research, portfolio discussion, design tools
   - For DevOps Engineers: infrastructure, CI/CD, monitoring, cloud platforms

3. BEHAVIORAL PHASE: Ask 3-5 behavioral questions:
   - Tell me about a challenging project you worked on
   - How do you handle conflicts with team members?
   - Describe a time you had to learn something new quickly
   - What motivates you in your work?
   - How do you prioritize tasks when everything seems urgent?

4. CLOSING PHASE: Wrap up the interview, ask if they have questions, explain next steps.

IMPORTANT RULES:
- Be conversational and natural, like a human interviewer
- Listen actively and ask follow-up questions based on their responses
- Score responses on a 1-5 scale (1=poor, 5=excellent)
- Take notes on interesting points or concerns
- Move through phases naturally based on conversation flow
- Be encouraging but professional
- Allow for interruptions and natural conversation flow
- If they give a brief answer, ask for more details or examples
- Adapt your questions based on their experience level

SCORING GUIDELINES:
- 5: Exceptional answer with clear examples, deep understanding
- 4: Good answer with solid examples and understanding
- 3: Adequate answer, meets basic expectations
- 2: Below average, lacks depth or has gaps
- 1: Poor answer, significant concerns

Use the provided functions to record information and manage the interview flow."""

WELCOME_MESSAGE = "Hello! Welcome to your interview today. I'm excited to speak with you. Could you please start by telling me your name and what position you're interviewing for?"

TECHNICAL_INTERVIEW_PROMPTS = {
    "software_engineer": [
        "Can you walk me through how you would design a system to handle millions of users?",
        "Tell me about a challenging bug you had to debug. How did you approach it?",
        "What's your experience with different programming languages and frameworks?",
        "How do you ensure code quality in your projects?",
        "Describe a time you had to optimize code for performance."
    ],
    "data_scientist": [
        "How would you approach a new machine learning project from start to finish?",
        "What's your experience with different ML algorithms and when to use them?",
        "How do you handle missing or dirty data in your datasets?",
        "Can you explain cross-validation and why it's important?",
        "Tell me about a time you had to explain complex technical results to non-technical stakeholders."
    ],
    "product_manager": [
        "How do you prioritize features when you have limited development resources?",
        "Tell me about a product you launched. What was your process?",
        "How do you gather and validate user requirements?",
        "What metrics would you use to measure product success?",
        "Describe a time you had to make a difficult product decision."
    ],
    "designer": [
        "Walk me through your design process for a new feature or product.",
        "How do you conduct user research and incorporate feedback?",
        "Tell me about a design challenge you faced and how you solved it.",
        "How do you collaborate with developers and product managers?",
        "What's your approach to creating accessible designs?"
    ],
    "devops_engineer": [
        "How would you design a CI/CD pipeline for a multi-service application?",
        "Tell me about your experience with infrastructure as code.",
        "How do you handle monitoring and alerting in production systems?",
        "Describe a time you had to troubleshoot a critical production issue.",
        "What's your approach to ensuring security in cloud environments?"
    ]
}

BEHAVIORAL_QUESTIONS = [
    "Tell me about a challenging project you worked on. What made it challenging and how did you handle it?",
    "Describe a time when you had to work with a difficult team member. How did you handle the situation?",
    "Can you give me an example of a time you had to learn a new technology or skill quickly?",
    "Tell me about a time you made a mistake at work. How did you handle it?",
    "Describe a situation where you had to meet a tight deadline. How did you prioritize your work?",
    "Give me an example of when you had to convince someone to see things your way.",
    "Tell me about a time you received constructive criticism. How did you respond?",
    "Describe a situation where you had to work with limited resources or constraints.",
    "Can you tell me about a time you went above and beyond what was expected?",
    "How do you stay current with industry trends and technologies?"
]

FOLLOW_UP_PROMPTS = [
    "Can you give me a specific example?",
    "What was the outcome of that situation?",
    "How did you measure success in that project?",
    "What would you do differently if you faced a similar situation again?",
    "What did you learn from that experience?",
    "Can you elaborate on that a bit more?",
    "What challenges did you face during that process?",
    "How did your team react to that approach?"
]

CLOSING_MESSAGE = """Thank you so much for taking the time to interview with us today. I really enjoyed our conversation and learning more about your background and experience. 

Do you have any questions about the role, the team, or the company that I can answer for you?

We'll be in touch soon with next steps. Thanks again, and have a great rest of your day!"""

PHASE_TRANSITION_MESSAGES = {
    "technical": "Great! Now I'd like to ask you some technical questions related to the role.",
    "behavioral": "Excellent! Let's shift gears and talk about some situational and behavioral aspects.",
    "closing": "Thank you for those insights. Let me wrap up with some final questions."
}

def get_technical_questions(position: str) -> list:
    """Get technical questions based on the position"""
    position_clean = position.lower().replace(" ", "_")
    return TECHNICAL_INTERVIEW_PROMPTS.get(position_clean, TECHNICAL_INTERVIEW_PROMPTS["software_engineer"])

def get_random_behavioral_question() -> str:
    """Get a random behavioral question"""
    import random
    return random.choice(BEHAVIORAL_QUESTIONS)

def get_follow_up_prompt() -> str:
    """Get a random follow-up prompt"""
    import random
    return random.choice(FOLLOW_UP_PROMPTS)