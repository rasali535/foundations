import { useEffect } from 'react';

const SEO = ({ title, description }) => {
    useEffect(() => {
        if (title) {
            document.title = `${title} | Foundations Counselling Academy`;
        }
        if (description) {
            let metaDesc = document.querySelector('meta[name="description"]');
            if (metaDesc) {
                metaDesc.setAttribute('content', description);
            } else {
                metaDesc = document.createElement('meta');
                metaDesc.setAttribute('name', 'description');
                metaDesc.setAttribute('content', description);
                document.head.appendChild(metaDesc);
            }
        }
    }, [title, description]);

    return null;
};

export default SEO;
