COURSE_DATABASE = {
    "python": {
        "course_name": "Python for Everybody Specialization",
        "platform": "Coursera",
        "url": "https://www.coursera.org/specializations/python"
    },
    "machine learning": {
        "course_name": "Machine Learning Specialization",
        "platform": "Coursera",
        "url": "https://www.coursera.org/specializations/machine-learning-introduction"
    },
    "docker": {
        "course_name": "Docker for the Absolute Beginner",
        "platform": "Udemy",
        "url": "https://www.udemy.com/course/learn-docker/"
    },
    "kubernetes": {
        "course_name": "Certified Kubernetes Administrator (CKA)",
        "platform": "Udemy",
        "url": "https://www.udemy.com/course/certified-kubernetes-administrator-with-practice-tests/"
    },
    "react": {
        "course_name": "Meta Front-End Developer Professional Certificate",
        "platform": "Coursera",
        "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"
    },
    "sql": {
        "course_name": "The Complete SQL Bootcamp",
        "platform": "Udemy",
        "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"
    },
    "aws": {
        "course_name": "AWS Certified Solutions Architect",
        "platform": "Coursera",
        "url": "https://www.coursera.org/professional-certificates/aws-cloud-solutions-architect"
    }
}

def get_courses_for_skills(missing_skills: list) -> list:
    recommendations = []
    for skill in missing_skills:
        key = skill.strip().lower()
        matched_key = next((k for k in COURSE_DATABASE if k in key or key in k), None)
        if matched_key:
            rec = COURSE_DATABASE[matched_key].copy()
            rec["skill"] = skill
            recommendations.append(rec)
        else:
            recommendations.append({
                "skill": skill,
                "course_name": f"Learn {skill} on Coursera",
                "platform": "Coursera",
                "url": f"https://www.coursera.org/search?query={skill.replace(' ', '%20')}"
            })
    return recommendations