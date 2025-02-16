document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysisForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const spinner = analyzeBtn.querySelector('.spinner-border');
    const resultsSection = document.getElementById('resultsSection');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Show loading state
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

            // Update results
            updateResults(data, statement);
            resultsSection.classList.remove('d-none');

        } catch (error) {
            console.error('Error:', error);
            alert(`Fehler bei der Analyse: ${error.message}`);
        } finally {
            // Reset loading state
            analyzeBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
});

function updateResults(data, statement) {
    const resultsDiv = document.getElementById('explanations');
    resultsDiv.innerHTML = '';

    // Sort parties by agreement score
    const sortedParties = Object.entries(data)
        .map(([party, info]) => ({
            party,
            ...info
        }))
        .sort((a, b) => b.agreement - a.agreement);

    // Define the groups
    const groups = [
        {
            title: 'Höchste Übereinstimmung',
            filter: party => party.agreement >= 70,
            class: 'border-success'
        },
        {
            title: 'Teilweise Übereinstimmung',
            filter: party => party.agreement >= 40 && party.agreement < 70,
            class: 'border-info'
        },
        {
            title: 'Geringe Übereinstimmung',
            filter: party => party.agreement >= 10 && party.agreement < 40,
            class: 'border-warning'
        },
        {
            title: 'Keine klare Position',
            filter: party => party.agreement < 10,
            class: 'border-secondary'
        }
    ];

    // Create container for groups
    const groupsContainer = document.createElement('div');
    groupsContainer.className = 'groups-container';

    // Track used parties to ensure each appears only once
    const usedParties = new Set();

    // Distribute parties into groups
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

                // Create citations HTML
                const citationsHtml = `
                    <div class="collapse" id="citations-${partyInfo.party}">
                        <div class="mt-3 citations">
                            <h6 class="mb-2">Quellen & Zitate:</h6>
                            ${partyInfo.citations && partyInfo.citations.length > 0 
                                ? partyInfo.citations.map(citation => `
                                    <div class="citation mb-2">
                                        <blockquote class="blockquote mb-1">
                                            <p class="mb-0">${citation.text}</p>
                                        </blockquote>
                                        <footer class="blockquote-footer">
                                            Quelle: ${citation.source}${citation.page ? `, Seite ${citation.page}` : ''}
                                        </footer>
                                    </div>
                                `).join('')
                                : '<p class="text-muted">Keine Zitate verfügbar.</p>'
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
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">${getPartyFullName(partyInfo.party)}</h5>
                            <span class="badge bg-primary">${partyInfo.agreement}%</span>
                        </div>
                        <p class="mt-2 mb-0">${partyInfo.explanation}</p>
                        <div class="d-flex gap-2 mt-3">
                            <button class="btn btn-link" type="button" data-bs-toggle="collapse" data-bs-target="#citations-${partyInfo.party}">
                                <i class="fas fa-quote-left me-1"></i>Quellen anzeigen
                            </button>
                            <div class="btn-group">
                                <button class="btn btn-outline-primary btn-sm" onclick='sharePartyAnalysis("twitter", ${JSON.stringify(shareData)})'>
                                    <i class="fab fa-twitter"></i>
                                </button>
                                <button class="btn btn-outline-primary btn-sm" onclick='sharePartyAnalysis("facebook", ${JSON.stringify(shareData)})'>
                                    <i class="fab fa-facebook"></i>
                                </button>
                                <button class="btn btn-outline-primary btn-sm" onclick='sharePartyAnalysis("linkedin", ${JSON.stringify(shareData)})'>
                                    <i class="fab fa-linkedin"></i>
                                </button>
                            </div>
                        </div>
                        ${citationsHtml}
                    </div>
                `;
                groupDiv.appendChild(partyDiv);
            });

            groupsContainer.appendChild(groupDiv);
        }
    });

    resultsDiv.appendChild(groupsContainer);
}

function sharePartyAnalysis(platform, data) {
    const text = `Analyse: "${data.statement}"\n\n${data.party}: ${data.agreement}% Übereinstimmung\n${data.explanation}`;
    const encodedText = encodeURIComponent(text);

    let url;
    switch (platform) {
        case 'twitter':
            url = `https://twitter.com/intent/tweet?text=${encodedText}`;
            break;
        case 'facebook':
            url = `https://www.facebook.com/sharer/sharer.php?u=${window.location.href}&quote=${encodedText}`;
            break;
        case 'linkedin':
            url = `https://www.linkedin.com/sharing/share-offsite/?url=${window.location.href}&summary=${encodedText}`;
            break;
    }

    window.open(url, '_blank', 'width=600,height=400');
}

function getPartyFullName(partyKey) {
    const partyNames = {
        'afd': 'Alternative für Deutschland',
        'bsw': 'Bündnis Sahra Wagenknecht',
        'cdu_csu': 'CDU/CSU',
        'linke': 'DIE LINKE',
        'fdp': 'Freie Demokratische Partei',
        'gruene': 'BÜNDNIS 90/DIE GRÜNEN',
        'spd': 'Sozialdemokratische Partei Deutschlands'
    };
    return partyNames[partyKey] || partyKey;
}