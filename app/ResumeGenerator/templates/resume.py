from typing import Dict, List
from .utils import escape_latex, format_date_for_latex, read_template_file
import yaml


class Resume:
    def get_full_name(self, user_data: Dict) -> str:
        full_name_list = [user_data.get('first_name') or '', user_data.get('middle_name') or '', user_data.get('last_name') or '']
        return ' '.join(part for part in full_name_list if part)

    def getVerticalSpacing(self, spacing: int) -> str:
        return "\\vspace{" + str(spacing) + "}\n\n"

    def generate_title_section(self, user_data: Dict) -> str:
        # Map of link types to their URL prefixes and icon names
        def display(x):
            x = x.replace('https://', '').replace('www.', '')
            return x
        
        link_config = {
            'phone': {'prefix': 'tel:', 'icon': 'Phone', 'display': display},
            'email': {'prefix': 'mailto:', 'icon': 'Envelope', 'display': display},
            'linkedin_url': {'prefix': '', 'icon': 'Linkedin', 'display': display},
            'github_url': {'prefix': '', 'icon': 'Github', 'display': display},
            'hackerrank_url': {'prefix': '', 'icon': 'Hackerrank', 'display': display},
            'leetcode_url': {'prefix': '', 'icon': 'Code', 'display': lambda x: 'LeetCode: ' + display(x)}
        }
        
        links = []
        if user_data.get('phone'):
            links.append(('phone', user_data.get('phone')))
        if user_data.get('email'):
            links.append(('email', user_data.get('email')))
        if user_data.get('linkedin_url'):
            links.append(('linkedin_url', user_data.get('linkedin_url')))
        if user_data.get('github_url'):
            links.append(('github_url', user_data.get('github_url')))
        if user_data.get('hackerrank_url'):
            links.append(('hackerrank_url', user_data.get('hackerrank_url')))
        if user_data.get('leetcode_url'):
            links.append(('leetcode_url', user_data.get('leetcode_url')))

        body = ""
        for i, (link_type, link_value) in enumerate(links, 1):
            if i > 1 and (i - 1) % 3 == 0:
                body += "    \\\\\n"
            
            config = link_config[link_type]
            url = config['prefix'] + link_value
            display_text = config['display'](link_value)
            
            fa_cmd = "\\" + "fa" + config['icon']  # Build \faPhone, \faEnvelope, etc.
            body += "    \\href{" + url + "}{" + fa_cmd + "~" + escape_latex(display_text) + "}"
            
            # Add spacing after each link (except the last one)
            if i < len(links):
                body += " \\hspace{10pt}\n"
            else:
                body += "\n"
        
        portfolio_title = escape_latex(user_data.get('portfolio_title', ''))
        if portfolio_title:
            portfolio_title += "\\\\"
        
        return read_template_file("v1/title.txt")\
            .replace("<FULL_NAME>", escape_latex(self.get_full_name(user_data)))\
            .replace("<PORTPOLIO_TITLE>", portfolio_title)\
            .replace("<TITLE_BODY>", body)

    def group_skills_by_category(self, skills: List[Dict]) -> Dict[str, List[Dict]]:
        skills_by_category: Dict[str, List[Dict]] = {}
        for skill in skills:
            category = skill.get('category', 'Other')
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill.get('name', ''))
        return skills_by_category

    def generate_skills_section(self, config: Dict, skills: List[Dict]) -> str:
        skills_by_category = self.group_skills_by_category(skills)
        if skills_by_category == {}:
            return ""

        skill_body = ""
        for category, skill_names in skills_by_category.items():
            # skill_names is already a list of strings, so join them directly
            skills_list = ", ".join([escape_latex(name) for name in skill_names])
            skill_body += "        \\item{\\textbf{\\normalsize{" + escape_latex(category) + ":}} { \\normalsize{" + skills_list + "}}}\n"
            skill_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_BULLET_POINTS'])

        return read_template_file("v1/skills.txt")\
            .replace("<SKILL_BODY>", skill_body)

    def generate_experience_section(self, config: Dict, experiences: List[Dict]) -> str:
        if len(experiences) == 0:
            return ""
        
        content = "\\section{EXPERIENCE} {\n"
        content += "    \\resumeSubHeadingListStart\n"

        experience_body = ""
        for i, experience in enumerate(sorted(experiences, key=lambda x: x.get('start_date') or '', reverse=True)):
            if i > 0:
                experience_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTIONS'])
            experience_body += "        \\resumeSubheading\n"
            experience_body += "            {" + escape_latex(experience.get('title', '')) + " (" + escape_latex(experience.get('company', '')) + ")}{" + format_date_for_latex(experience.get('start_date', '')) + " -- " + format_date_for_latex(experience.get('end_date', '')) + "}\n"
            experience_body += "            {}{}\n"
            experience_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_ITEM_TITLE_AND_CONTENT'])
            experience_body += "        \\resumeItemListStart\n"
            for i, subdesc in enumerate(experience.get('description', '').split('\n')):
                if i > 0:
                    experience_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_BULLET_POINTS'])
                if subdesc.strip():
                    experience_body += "            \\resumeItem{" + escape_latex(subdesc.strip()) + "}\n"
            experience_body += "        \\resumeItemListEnd\n"

        return read_template_file("v1/experience.txt")\
            .replace("<EXPERIENCE_BODY>", experience_body)

    def generate_education_section(self, config: Dict, educations: List[Dict]) -> str:
        if len(educations) == 0:
            return ""
        
        education_body = ""
        for i, education in enumerate(sorted(educations, key=lambda x: x.get('start_date', ''), reverse=True)):
            if i > 0:
                education_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTIONS'])
            education_body += "        \\resumeSubheading\n"
            education_body += "            {" + escape_latex(education.get('institution', '')) + "}{" + format_date_for_latex(education.get('start_date', '')) + " -- " + format_date_for_latex(education.get('end_date', '')) + "}\n"
            education_body += "            {}{}\n"
            education_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_ITEM_TITLE_AND_CONTENT'])
            education_body += "        \\resumeItemListStart\n"
            for i, subdesc in enumerate((education.get('description') or '').split('\n')):
                if i > 0:
                    education_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_BULLET_POINTS'])
                if subdesc.strip():
                    education_body += "            \\resumeItem{" + escape_latex(subdesc.strip()) + "}\n"
            education_body += "        \\resumeItemListEnd\n"

        return read_template_file("v1/education.txt")\
            .replace("<EDUCATION_BODY>", education_body)

    def generate_project_section(self, config: Dict, projects: List[Dict]) -> str:
        if len(projects) == 0:
            return ""
        
        project_body = ""
        for i, project in enumerate(sorted(projects, key=lambda x: x.get('start_date', ''), reverse=True)):
            if i > 0:
                project_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTIONS'])
            project_body += "        \\resumeSubheading\n"
            project_body += "            {" + escape_latex(project.get('title', '')) + " }{" + format_date_for_latex(project.get('start_date', '')) + " -- " + format_date_for_latex(project.get('end_date', '')) + "}\n"
            project_body += "            {}{}\n"
            project_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_ITEM_TITLE_AND_CONTENT'])
            project_body += "        \\resumeItemListStart\n"
            tech_list = project.get('technologies', [])
            if tech_list:
                tech_str = ", ".join([escape_latex(str(t)) for t in tech_list])
                # Add technologies line without double-escaping
                project_body += "            \\resumeItem{Technologies: " + tech_str + "}\n"
            for i, subdesc in enumerate(project.get('description', '').split('\n')):
                if i > 0:
                    project_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_BULLET_POINTS'])
                if subdesc.strip():
                    project_body += "            \\resumeItem{" + escape_latex(subdesc.strip()) + "}\n"

            project_body += "        \\resumeItemListEnd\n"

        return read_template_file("v1/project.txt")\
            .replace("<PROJECT_BODY>", project_body)

    def generate_achievement_section(self, config: Dict, awards: List[Dict]) -> str:
        if len(awards) == 0:
            return ""
        
        achievement_body = ""
        for i, award in enumerate(awards):
            if i > 0:
                achievement_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTIONS'])
            achievement_body += "        \\resumeSubheading\n"
            achievement_body += "            {" + escape_latex(award.get('name', '')) + " (" + escape_latex(award.get('issuer', '')) + ")}{" + format_date_for_latex(award.get('issue_date', '')) + "}\n"
            achievement_body += "            {}{}\n"
            achievement_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_ITEM_TITLE_AND_CONTENT'])
            achievement_body += "        \\resumeItemListStart\n"
            for i, subdesc in enumerate((award.get('description') or '').split('\n')):
                if i > 0:
                    achievement_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_BULLET_POINTS'])
                if subdesc.strip():
                    achievement_body += "        \\resumeItem{" + escape_latex(subdesc.strip()) + "}\n"
            achievement_body += "        \\resumeItemListEnd\n"

        return read_template_file("v1/achievement.txt")\
            .replace("<ACHIEVEMENT_BODY>", achievement_body)

    def generate_certification_section(self, config: Dict, certifications: List[Dict]) -> str:
        if len(certifications) == 0:
            return ""
        
        certification_body = ""
        for i, certification in enumerate(certifications):
            if i > 0:
                certification_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTIONS'])
            certification_body += "        \\resumeSubheading\n"
            certification_body += "            {" + escape_latex(certification.get('name', '')) + " (" + escape_latex(certification.get('issuer', '')) + ")}{" + format_date_for_latex(certification.get('issue_date', '')) + "}\n"
            certification_body += "            {}{}\n"
            certification_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_ITEM_TITLE_AND_CONTENT'])
            certification_body += "        \\resumeItemListStart\n"
            for i, subdesc in enumerate((certification.get('description') or '').split('\n')):
                if i > 0:
                    certification_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SUB_SECTION_BULLET_POINTS'])
                if subdesc.strip():
                    certification_body += "            \\resumeItem{" + escape_latex(subdesc.strip()) + "}\n"
            certification_body += "        \\resumeItemListEnd\n"

        return read_template_file("v1/certification.txt")\
            .replace("<CERTIFICATION_BODY>", certification_body)

    def generate_resume(self, user_data: Dict, experiences: List[Dict], educations: List[Dict], projects: List[Dict], skills: List[Dict], certifications: List[Dict], awards: List[Dict]) -> str:
        template_content = read_template_file("v1/template.txt")
        methods_content = read_template_file("v1/methods.txt")
        config = yaml.safe_load(read_template_file("v1/config.yml"))

        sections = [{'title': 'TITLE', 'content': self.generate_title_section(user_data)},
                    {'title': 'SKILLS', 'content': self.generate_skills_section(config, skills)},
                    {'title': 'EXPERIENCE', 'content': self.generate_experience_section(config, experiences)},
                    {'title': 'EDUCATION', 'content': self.generate_education_section(config, educations)},
                    {'title': 'PROJECTS', 'content': self.generate_project_section(config, projects)},
                    {'title': 'ACHIEVEMENTS', 'content': self.generate_achievement_section(config, awards)},
                    {'title': 'CERTIFICATIONS', 'content': self.generate_certification_section(config,certifications)}]

        resume_body = ""
        i = 0
        for section in sections:
            if i > 0:
                resume_body += self.getVerticalSpacing(config['SPACE_BETWEEN_SECTIONS'])
            if section['content'] == "":
                continue
            resume_body += section['content'] + "\n"
            i += 1

        content = read_template_file("v1/resume.txt")\
            .replace("<TEMPLATE_CONTENT>", template_content)\
            .replace("<METHODS_CONTENT>", methods_content)\
            .replace("<RESUME_BODY>", resume_body)

        return content