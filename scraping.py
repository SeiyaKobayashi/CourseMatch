from bs4 import BeautifulSoup
import requests

# Scrapes list of Schools
def scrapeSchools(URL):
    soup = BeautifulSoup(requests.get(URL).text, "html.parser")
    rawData = soup.select('.school')
    schoolsData = []

    for i in range(len(rawData)):
        schoolsData.append({'school': rawData[i].find('h3').text,
                            'link': 'https://www.bu.edu' + rawData[i].find_all('a')[-1]['href'] + 'courses/'})

    return schoolsData

# Scrapes list of departments (name + link)
def scrapeDepartments(URL):
    soup = BeautifulSoup(requests.get(URL).text, "html.parser")
    rawData = soup.select('.level_2')
    departmentsData = []

    # For school with no sub departments and med-school
    if (len(rawData) == 0) or (len(rawData) == 1 and rawData[0].contents[0] == 'Clerkships & Sub-internships'):
        departmentsData.append({'department': 'No Sub-Departments',
                                'link': URL})
    else:
        for i in range(len(rawData)):
            departmentsData.append({'department': rawData[i].contents[0],
                                    'link': rawData[i]['href']})

    return departmentsData

# Scrapes list of courses (name + link)
def scrapeCourses(departmentURL):
    soup_all = BeautifulSoup(requests.get(departmentURL).text, "html.parser")
    if soup_all.find('div', {'class': 'pagination'}) == None:
        numOfPages = 1
    else:
        numOfPages = len(soup_all.find('div', {'class': 'pagination'}).find_all('a')) + 1

    rawData = []
    coursesData = []

    for i in range(numOfPages):
        if i == 0:
            soup = BeautifulSoup(requests.get(departmentURL).text, "html.parser")
        else:
            soup = BeautifulSoup(requests.get(departmentURL+str(i+1)+'/').text, "html.parser")
        rawData.extend(soup.find('ul', {'class': 'course-feed'}).find_all('li', {'class': None}))

    for j in range(len(rawData)):
        coursesData.append({'course': rawData[j].find('a').text,
                            'link': 'https://www.bu.edu' + rawData[j].find('a')['href']})

    return coursesData

# Too slow
# def scrapeCourseDescription(courseURL):
#     soup = BeautifulSoup(requests.get(courseURL).text, "html.parser")
#     descriptionData = soup.find('div', {'id': 'course-content'}).find('p').text
#
#     return descriptionData
