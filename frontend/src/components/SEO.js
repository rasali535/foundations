import { useEffect } from 'react';
import { SITE } from '../data/site';

const SEO = ({ title, description, path = "" }) => {
    useEffect(() => {
        const fullTitle = title 
            ? `${title} | Foundations Counselling Academy` 
            : `${SITE.name} | People first. Practical support. Sustainable performance.`;
        
        document.title = fullTitle;

        const canonicalUrl = `${SITE.canonicalUrl}${path.startsWith('/') ? path : `/${path}`}`;
        const defaultDesc = description || "Evidence-based counselling, workplace wellness, corporate training and practical online programmes from Gaborone, Botswana to wherever you are.";

        // Update meta tags helper
        const setMeta = (name, content, attr = 'name') => {
            let el = document.querySelector(`meta[${attr}="${name}"]`);
            if (el) {
                el.setAttribute('content', content);
            } else {
                el = document.createElement('meta');
                el.setAttribute(attr, name);
                el.setAttribute('content', content);
                document.head.appendChild(el);
            }
        };

        setMeta('description', defaultDesc);
        setMeta('og:title', fullTitle, 'property');
        setMeta('og:description', defaultDesc, 'property');
        setMeta('og:url', canonicalUrl, 'property');
        setMeta('og:site_name', SITE.name, 'property');
        setMeta('og:type', 'website', 'property');
        setMeta('twitter:card', 'summary_large_image');
        setMeta('twitter:title', fullTitle);
        setMeta('twitter:description', defaultDesc);

        // Canonical link
        let canonicalEl = document.querySelector('link[rel="canonical"]');
        if (canonicalEl) {
            canonicalEl.setAttribute('href', canonicalUrl);
        } else {
            canonicalEl = document.createElement('link');
            canonicalEl.setAttribute('rel', 'canonical');
            canonicalEl.setAttribute('href', canonicalUrl);
            document.head.appendChild(canonicalEl);
        }

        // Schema.org Structured Data
        const schemaId = 'fca-schema-org';
        let scriptEl = document.getElementById(schemaId);
        if (!scriptEl) {
            scriptEl = document.createElement('script');
            scriptEl.id = schemaId;
            scriptEl.type = 'application/ld+json';
            document.head.appendChild(scriptEl);
        }

        const schemaData = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": `${SITE.canonicalUrl}/#organization`,
                    "name": SITE.name,
                    "url": SITE.canonicalUrl,
                    "logo": `${SITE.canonicalUrl}${SITE.logo}`,
                    "email": SITE.email,
                    "telephone": SITE.phone,
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "Plot 18680 Khuhurutse St, Phase 2",
                        "addressLocality": "Gaborone",
                        "addressCountry": "BW"
                    }
                },
                {
                    "@type": "LocalBusiness",
                    "@id": `${SITE.canonicalUrl}/#localbusiness`,
                    "name": SITE.name,
                    "url": SITE.canonicalUrl,
                    "telephone": SITE.phone,
                    "priceRange": "$$",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "Plot 18680 Khuhurutse St, Phase 2",
                        "addressLocality": "Gaborone",
                        "addressCountry": "BW"
                    },
                    "openingHoursSpecification": [
                        {
                            "@type": "OpeningHoursSpecification",
                            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                            "opens": "09:00",
                            "closes": "17:00"
                        },
                        {
                            "@type": "OpeningHoursSpecification",
                            "dayOfWeek": ["Saturday"],
                            "opens": "09:00",
                            "closes": "13:00"
                        }
                    ]
                }
            ]
        };

        scriptEl.textContent = JSON.stringify(schemaData);

    }, [title, description, path]);

    return null;
};

export default SEO;
