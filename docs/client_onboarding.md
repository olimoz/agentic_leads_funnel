# AI Agent Leads Generation

David, the below headlines represent the key prompts to agents in the lead funnel. Their instructions, which are wrapped in triple quiotes ("""..."""), are currently for the video production company. Please adapt them for your business. The scoring agent is the most sensitive, take time to get the scoring agent close to how you would approach the task.

## Scoring Agent

"""
Our objective is to score a business_text for its potential to help us promote video production services to a specific person, the target. 
Those videos are best targetted at people and businesses who have recent case studies, news and events to promote. 
In order to give us the detail we need for marketing, a high scoring text will give us case studies, news and activities which were specifically engaged in by that target person working for that target business during the target period.
Your task is to score the text for how well it meets our objective. This 'Target Score' is additive and is applied as per the following metrics:

A. Text mentions case studies specifically relating to the person and company in the period: +3.
B. Text mentions news, events and blogs (other than case studies) specifically relating to the person working the company in the period: +2.
C. Text gives details of activities which the target person engaged in, during the period: +1.
D. Text mentions a recent fact about the person or business which is clearly deserving of a social media video, regardless of precise period: +4.

Max Score =10
Min Score = 0
"""

## Ranking Agent (Tie Breaker)

"""
We are a business of video producers. We are seeking to promote our services for the production of videos for corporate marketing, typically 5mins per video in  interview format. We have been successful in pitching our services to companies who have recent achievements to promote. Most notably, recent case studies, product launches, site openings or competition wins, all these types of stories provide for good material.

You are tasked with studying and ranking the below texts for their potential for buying our video production services. When considering rankings, ask yourself these questions:
1. Does the text describe something which the client would likely promote via a short video? If yes, then rank higher.
2. Does the text contain sufficient detail that we could prepare a detailed pitch to the client for our services? If yes, then rank higher.
3. Does the text contain urls, links for us to dig deeper into the results? If yes, then rank higher.

You must rank the below texts. The highest rank (most potential for a video and most details) is rank 1. 
"""

## Business Description

David, this is used to generate the proposed communications to the the leads. Optimal is a list of case studies, then the agent can find the case study most appropriate for the lead. At least 500 words, preferably 1000. 

"""
Please enter your text here...
"""

### Email Template

David, as discussed, the agents will shortlist the leads with the highest potential and then propose an email communication specific to each selected lead.

"""
Hi {first_name}, 

Congratulations on <mention the client's most recent case study, news or product launch>

A short form video can promote your success to a wide audience on social media or via your website. It can take as little as a day to produce. 
We have two decades of experience, for example <insert relevant experience here>.

Regards,

First_Name Last_Name
Job title
Company name
Mobile phone number

Companmy Strap Line

"""

