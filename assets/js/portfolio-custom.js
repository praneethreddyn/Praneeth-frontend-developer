(function(){
  'use strict';
  document.addEventListener('DOMContentLoaded', function(){
    var year = document.getElementById('year');
    if (year) year.textContent = new Date().getFullYear();
    if (window.AOS && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      window.AOS.init({ duration: 650, once: true, offset: 70 });
    }
    var links = document.querySelectorAll('.top-nav a');
    links.forEach(function(link){
      link.addEventListener('click', function(){
        links.forEach(function(item){ item.removeAttribute('aria-current'); });
        link.setAttribute('aria-current','location');
      });
    });

    var projectsContainer = document.getElementById('github-projects');
    var projectsStatus = document.getElementById('github-projects-status');

    function apiUrl(path){
      var isLocalhost = window.location.protocol === 'http:' &&
        (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
      if (isLocalhost && window.location.port !== '8000') {
        return 'http://127.0.0.1:8000' + path;
      }
      return path;
    }

    function fetchRepositories(){
      return fetch(apiUrl('/api/repositories')).then(function(response){
        if (!response.ok) throw new Error('Portfolio API returned ' + response.status);
        return response.json();
      }).catch(function(apiError){
        console.warn('The local repository API is unavailable; loading directly from GitHub.', apiError);
        var repositories = [];
        var page = 1;
        function fetchPage(){
          return fetch('https://api.github.com/users/praneethreddyn/repos?type=owner&sort=updated&per_page=100&page=' + page)
            .then(function(response){
              if (!response.ok) throw new Error('GitHub API returned ' + response.status);
              return response.json();
            })
            .then(function(items){
              if (!Array.isArray(items)) throw new Error('GitHub returned an unexpected repository list.');
              repositories = repositories.concat(items);
              if (items.length === 100) {
                page += 1;
                return fetchPage();
              }
              return repositories.filter(function(repository){
                return repository && repository.name &&
                  repository.name.toLowerCase() !== 'praneeth-frontend-developer';
              });
            });
        }
        return fetchPage();
      });
    }

    function renderRepositories(repositories){
      if (!projectsContainer || !projectsStatus) return;
      if (!Array.isArray(repositories)) throw new Error('Repository response was not a list.');
      projectsContainer.replaceChildren();
      repositories.filter(function(repository){
        return repository && repository.name &&
          repository.name.toLowerCase() !== 'praneeth-frontend-developer';
      }).forEach(function(repository){
        if (!repository || !repository.name || !repository.html_url) return;
        var card = document.createElement('article');
        card.className = 'github-project';

        var title = document.createElement('h4');
        var link = document.createElement('a');
        link.href = repository.html_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = repository.name;
        title.appendChild(link);

        var description = document.createElement('p');
        description.textContent = repository.description || 'No description provided for this repository.';

        var details = document.createElement('div');
        details.className = 'github-project-meta';
        var language = document.createElement('span');
        language.textContent = repository.language || 'Repository';
        details.appendChild(language);
        if (repository.updated_at) {
          var updated = document.createElement('span');
          updated.textContent = 'Updated ' + new Date(repository.updated_at).toLocaleDateString();
          details.appendChild(updated);
        }

        card.appendChild(title);
        card.appendChild(description);
        card.appendChild(details);
        projectsContainer.appendChild(card);
      });
      projectsStatus.textContent = repositories.length + ' repositories loaded from GitHub.';
    }

    if (projectsContainer && projectsStatus) {
      fetchRepositories().then(renderRepositories).catch(function(error){
        projectsStatus.textContent = 'Could not load GitHub repositories: ' + error.message;
      });
    }

    var resumeButton = document.getElementById('resume-download');
    var resumeStatus = document.getElementById('resume-download-status');
    if (resumeButton && resumeStatus) {
      function downloadResumeTemplate(){
        var downloadLink = document.createElement('a');
        downloadLink.href = 'Praneeth_Reddy_Nalamalapu_Resume.docx';
        downloadLink.download = 'Praneeth_Reddy_Nalamalapu_Resume.docx';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        downloadLink.remove();
      }

      resumeButton.addEventListener('click', function(){
        resumeButton.disabled = true;
        resumeStatus.textContent = 'Preparing your resume from the latest GitHub repositories...';
        fetch(apiUrl('/api/resume')).then(function(response){
          if (!response.ok) {
            return response.json().catch(function(){ return {}; }).then(function(payload){
              throw new Error(payload.error || 'Resume download failed (HTTP ' + response.status + ').');
            });
          }
          return response.blob();
        }).then(function(file){
          var objectUrl = URL.createObjectURL(file);
          var downloadLink = document.createElement('a');
          downloadLink.href = objectUrl;
          downloadLink.download = 'Praneeth_Reddy_Nalamalapu_Resume.docx';
          document.body.appendChild(downloadLink);
          downloadLink.click();
          downloadLink.remove();
          URL.revokeObjectURL(objectUrl);
          resumeStatus.textContent = 'Resume downloaded.';
        }).catch(function(error){
          downloadResumeTemplate();
          resumeStatus.textContent = 'Downloaded the saved resume template. To include the latest GitHub repositories, start the resume server with "python app.py" and try again. ' + error.message;
        }).finally(function(){
          resumeButton.disabled = false;
        });
      });
    }
  });
})();