<script>
    // Configuration
    const GITHUB_ORG = 'quantiota'; // Replace with your organization name

    // DOM Elements
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    // Event Listeners
    searchForm.addEventListener('submit', handleSearch);

    // Handle the search
    async function handleSearch(event) {
        event.preventDefault();
        const query = searchInput.value.trim();

        if (!query) return;

        searchResults.innerHTML = `<div class="loader">Searching...</div>`;

        try {
            const results = await searchRepositories(query);
            displayResults(results);
        } catch (error) {
            displayError(error.message);
        }
    }

    // Search repositories
    async function searchRepositories(query) {
        const apiUrl = `https://api.github.com/search/repositories?q=${encodeURIComponent(query)}+org:${GITHUB_ORG}`;

        try {
            const response = await fetch(apiUrl);
            console.log('API Response Status:', response.status);

            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error(`GitHub API rate limit exceeded. Please wait and try again later.`);
                }
                throw new Error(`GitHub API Error: ${response.status}`);
            }

            const data = await response.json();
            console.log('Search Results:', data);

            return data.items || [];
        } catch (error) {
            console.error('Search Error:', error);
            throw error;
        }
    }

    // Display results
    function displayResults(repositories) {
        if (!repositories.length) {
            searchResults.innerHTML = `
                <div class="repo-card no-results">
                    <p>No repositories found matching your search.</p>
                    <p>Tips:</p>
                    <ul>
                        <li>Check if the organization name is correct (${GITHUB_ORG})</li>
                        <li>Try different search terms</li>
                        <li>Make sure the repositories are public</li>
                    </ul>
                </div>
            `;
            return;
        }

        const html = repositories.map(repo => `
            <div class="repo-card">
                <h3><a href="${repo.html_url}" target="_blank" rel="noopener noreferrer">${repo.name}</a></h3>
                <p>${repo.description || 'No description available'}</p>
                <p>
                    ⭐ ${repo.stargazers_count} stars | 
                    🔤 ${repo.language || 'No language specified'} |
                    📅 Updated: ${new Date(repo.updated_at).toLocaleDateString()}
                </p>
            </div>
        `).join('');

        searchResults.innerHTML = html;
    }

    // Display error message
    function displayError(message) {
        searchResults.innerHTML = `
            <div class="error-message">
                <p>Error: ${message}</p>
                <p>Please try again later or contact support if the problem persists.</p>
            </div>
        `;
    }

    // Check URL for search parameter on page load
    document.addEventListener('DOMContentLoaded', () => {
        const urlParams = new URLSearchParams(window.location.search);
        const queryParam = urlParams.get('q');

        if (queryParam) {
            searchInput.value = queryParam;
            handleSearch(new Event('submit'));
        }
    });
</script>

