document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysisForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const spinner = analyzeBtn.querySelector('.spinner-border');
    const resultsSection = document.getElementById('resultsSection');
    const language = document.documentElement.lang || 'de'; // Default to German if not set

    // Text mappings for different languages
    const textMappings = {
        de: {
            highest: 'Höchste Übereinstimmung',
            partial: 'Teilweise Übereinstimmung',
            low: 'Geringe Übereinstimmung',
            none: 'Keine klare Position',
            source: 'Quelle',
            noCitations: 'Keine Zitate verfügbar.',
            showSources: 'Quellen anzeigen',
            share: 'Teilen'
        },
        en: {
            highest: 'Highest Match',
            partial: 'Partial Match',
            low: 'Low Match',
            none: 'No Clear Position',
            source: 'Source',
            noCitations: 'No citations available.',
            showSources: 'Show Sources',
            share: 'Share'
        }
    };

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        analyzeBtn.disabled = true;
        spinner.classList.remove('d-none');
        resultsSection.classList.add('d-none');

        const statement = document.getElementById('statement').value;

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ statement }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Analyse fehlgeschlagen');
            }

            if (!data || typeof data !== 'object') {
                throw new Error('Ungültige Antwort vom Server');
            }

            updateResults(data, statement);
            resultsSection.classList.remove('d-none');

        } catch (error) {
            console.error('Error:', error);
            alert(`Fehler bei der Analyse: ${error.message}`);
        } finally {
            analyzeBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });

    function updateResults(data, statement) {
        const resultsDiv = document.getElementById('explanations');
        resultsDiv.innerHTML = '';

        const sortedParties = Object.entries(data)
            .map(([party, info]) => ({
                party,
                ...info
            }))
            .sort((a, b) => b.agreement - a.agreement);

        const groups = [
            { title: textMappings[language].highest, filter: party => party.agreement >= 70, class: 'border-success' },
            { title: textMappings[language].partial, filter: party => party.agreement >= 40 && party.agreement < 70, class: 'border-info' },
            { title: textMappings[language].low, filter: party => party.agreement >= 10 && party.agreement < 40, class: 'border-warning' },
            { title: textMappings[language].none, filter: party => party.agreement < 10, class: 'border-secondary' }
        ];

        const groupsContainer = document.createElement('div');
        groupsContainer.className = 'groups-container';

        const usedParties = new Set();

        groups.forEach(group => {
            const groupParties = sortedParties.filter(party => 
                !usedParties.has(party.party) && group.filter(party)
            );

            if (groupParties.length > 0) {
                const groupDiv = document.createElement('div');
                groupDiv.className = 'group-section';
                groupDiv.innerHTML = `<h4 class="mb-3">${group.title}</h4>`;

                groupParties.forEach(partyInfo => {
                    usedParties.add(partyInfo.party);
                    const partyDiv = document.createElement('div');
                    partyDiv.className = `card mb-3 ${group.class}`;

                    // Create citations HTML with dynamic text
                    const citationsHtml = `
                        <div class="collapse" id="citations-${partyInfo.party}">
                            <div class="mt-3 citations">
                                <h6 class="mb-2">${textMappings[language].source} & Zitate:</h6>
                                ${partyInfo.citations && partyInfo.citations.length > 0 
                                    ? partyInfo.citations.map(citation => `
                                        <div class="citation mb-2">
                                            <blockquote class="blockquote mb-1">
                                                <p class="mb-0">${citation.text}</p>
                                            </blockquote>
                                            <footer class="blockquote-footer">
                                                ${textMappings[language].source}: ${citation.source}${citation.page ? `, Seite ${citation.page}` : ''}
                                            </footer>
                                        </div>
                                    `).join('')
                                    : `<p class="text-muted">${textMappings[language].noCitations}</p>`
                                }
                            </div>
                        </div>
                    `;

                    // Prepare social share data
                    const shareData = {
                        statement: statement.replace(/"/g, '&quot;'),
                        party: getPartyFullName(partyInfo.party),
                        agreement: partyInfo.agreement,
                        explanation: partyInfo.explanation.replace(/"/g, '&quot;')
                    };

                    partyDiv.innerHTML = `
                        <div class="card-body">
                            <h5 class="mb-0">${getPartyFullName(partyInfo.party)}</h5>
                            <span class="badge bg-primary">${partyInfo.agreement}%</span>
                            <p class="mt-2 mb-0">${partyInfo.explanation}</p>
                            <button class="btn btn-link" type="button" data-bs-toggle="collapse" data-bs-target="#citations-${partyInfo.party}">
                                <i class="fas fa-quote-left me-1"></i>${textMappings[language].showSources}
                            </button>
                            <div class="btn-group mt-2">
                                <button class="btn btn-outline-primary btn-sm" title="Share on Twitter" onclick='sharePartyAnalysis("twitter", ${JSON.stringify(shareData)})'>
                                    <i class="fab fa-twitter"></i> ${textMappings[language].share}
                                </button>
                                <button class="btn btn-outline-primary btn-sm" title="Share on Facebook" onclick='sharePartyAnalysis("facebook", ${JSON.stringify(shareData)})'>
                                    <i class="fab fa-facebook"></i> ${textMappings[language].share}
                                </button>
                                <button class="btn btn-outline-primary btn-sm" title="Share on LinkedIn" onclick='sharePartyAnalysis("linkedin", ${JSON.stringify(shareData)})'>
                                    <i class="fab fa-linkedin"></i> ${textMappings[language].share}
                                </button>
                            </div>
                        </div>
                        ${citationsHtml}
                    `;

                    groupDiv.appendChild(partyDiv);
                });

                groupsContainer.appendChild(groupDiv);
            }
        });

        resultsDiv.appendChild(groupsContainer);
    }

    // Added getPartyFullName function
    function getPartyFullName(partyKey) {
        const partyNames = {
            'afd': language === 'de' ? 'Alternative für Deutschland' : 'Alternative for Germany',
            'bsw': language === 'de' ? 'Bündnis Sahra Wagenknecht' : 'Alliance Sahra Wagenknecht',
            'cdu_csu': 'CDU/CSU',
            'linke': language === 'de' ? 'DIE LINKE' : 'The Left',
            'fdp': language === 'de' ? 'Freie Demokratische Partei' : 'Free Democratic Party',
            'gruene': language === 'de' ? 'BÜNDNIS 90/DIE GRÜNEN' : 'Alliance 90/The Greens',
            'spd': language === 'de' ? 'Sozialdemokratische Partei Deutschlands' : 'Social Democratic Party of Germany'
        };
        return partyNames[partyKey] || partyKey;
    }
});
