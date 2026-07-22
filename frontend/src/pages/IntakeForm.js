import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import SEO from '../components/SEO';
import './IntakeForm.css';

const IntakeForm = () => {
    const formspreeId = import.meta.env.VITE_FORMSPREE_ID || 'xdajqjev';
    const isPlaceholderId = formspreeId === 'YOUR_FORM_ID';

    const [step, setStep] = useState(1);
    
    const [formData, setFormData] = useState({
        full_name: '',
        dob: '',
        age: '',
        gender: '',
        phone: '',
        email: '',
        location: '',
        contact_method: 'Phone call',
        emergency_name: '',
        emergency_relationship: '',
        emergency_phone: '',
        reason: '',
        support: [],
        support_other: '',
        wellbeing_symptoms: [],
        self_harm: 'No',
        harm_others: 'No',
        unsafe: 'No',
        abuse: 'No',
        risk_details: '',
        previous_support_choice: 'No',
        previous_support_details: '',
        medication: 'No',
        readiness1: false,
        readiness2: false,
        readiness3: false,
        readiness4: false,
        consent_name: '',
        signature: '',
        consent_date: new Date().toISOString().substring(0, 10),
        office_practitioner: '',
        office_session_type: 'Virtual',
        office_date: '',
        office_fee: ''
    });

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitSuccess, setSubmitSuccess] = useState(false);
    const [submitError, setSubmitError] = useState('');

    useEffect(() => {
        const savedData = localStorage.getItem('pameltex_intake_draft');
        if (savedData) {
            try {
                setFormData(JSON.parse(savedData));
            } catch (e) {
                console.error("Error parsing saved intake form draft", e);
            }
        }
    }, []);

    const updateFormData = (fields) => {
        const updated = { ...formData, ...fields };
        setFormData(updated);
        localStorage.setItem('pameltex_intake_draft', JSON.stringify(updated));
    };

    const handleDobChange = (e) => {
        const dobVal = e.target.value;
        if (!dobVal) {
            updateFormData({ dob: dobVal, age: '' });
            return;
        }

        const birthDate = new Date(dobVal);
        const today = new Date();
        let calculatedAge = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
            calculatedAge--;
        }

        updateFormData({
            dob: dobVal,
            age: calculatedAge >= 0 ? calculatedAge.toString() : ''
        });
    };

    const handleSupportCheckbox = (value) => {
        const currentSupport = [...formData.support];
        const index = currentSupport.indexOf(value);
        if (index > -1) {
            currentSupport.splice(index, 1);
        } else {
            currentSupport.push(value);
        }
        updateFormData({ support: currentSupport });
    };

    const handleWellbeingCheckbox = (value) => {
        let currentSymptoms = [...formData.wellbeing_symptoms];
        if (value === 'None of the above') {
            if (currentSymptoms.includes('None of the above')) {
                currentSymptoms = [];
            } else {
                currentSymptoms = ['None of the above'];
            }
        } else {
            const noneIndex = currentSymptoms.indexOf('None of the above');
            if (noneIndex > -1) {
                currentSymptoms.splice(noneIndex, 1);
            }
            
            const index = currentSymptoms.indexOf(value);
            if (index > -1) {
                currentSymptoms.splice(index, 1);
            } else {
                currentSymptoms.push(value);
            }
        }
        updateFormData({ wellbeing_symptoms: currentSymptoms });
    };

    const handleAutofillDemo = () => {
        const demoData = {
            full_name: 'John Doe',
            dob: '1990-05-15',
            age: '36',
            gender: 'Male',
            phone: '+267 72 000 000',
            email: 'john.doe@example.com',
            location: 'Gaborone, Phase 2',
            contact_method: 'WhatsApp',
            emergency_name: 'Jane Doe',
            emergency_relationship: 'Spouse',
            emergency_phone: '+267 71 888 888',
            reason: 'I have been experiencing mild work-related stress and anxiety over the last 3 months due to project deadlines. Looking to learn stress management techniques.',
            support: ['Individual counselling', 'Work stress', 'Anxiety'],
            support_other: '',
            wellbeing_symptoms: ['Sleep difficulties', 'Work-related pressure', 'Anxiety or panic'],
            self_harm: 'No',
            harm_others: 'No',
            unsafe: 'No',
            abuse: 'No',
            risk_details: '',
            previous_support_choice: 'Yes',
            previous_support_details: 'Attended 2 counseling sessions back in 2022 for adjustment challenges. Found it helpful.',
            medication: 'No',
            readiness1: true,
            readiness2: true,
            readiness3: true,
            readiness4: true,
            consent_name: 'John Doe',
            signature: 'John Doe',
            consent_date: new Date().toISOString().substring(0, 10),
            office_practitioner: '',
            office_session_type: 'Virtual',
            office_date: '',
            office_fee: ''
        };
        updateFormData(demoData);
        alert('Form auto-filled with demo data! You can click through steps or submit to test.');
    };

    const validateStep = () => {
        if (step === 1) {
            if (!formData.full_name.trim()) return 'Full Name is required.';
            if (!formData.email.trim()) return 'Email Address is required.';
            if (!formData.phone.trim()) return 'Phone Number is required.';
        }
        if (step === 2) {
            if (!formData.emergency_name.trim()) return 'Emergency Contact Name is required.';
            if (!formData.emergency_phone.trim()) return 'Emergency Contact Phone Number is required.';
        }
        if (step === 3) {
            if (!formData.reason.trim()) return 'Please explain the reason you are seeking therapy.';
            if (formData.support.length === 0 && !formData.support_other.trim()) {
                return 'Please select at least one type of support needed or specify in "Other".';
            }
        }
        if (step === 4) {
            if (formData.wellbeing_symptoms.length === 0) {
                return 'Please select at least one wellbeing symptom or choose "None of the above".';
            }
            const hasRisk = formData.self_harm === 'Yes' || formData.harm_others === 'Yes' || formData.unsafe === 'Yes' || formData.abuse === 'Yes';
            if (hasRisk && !formData.risk_details.trim()) {
                return 'Please provide details in the explanation field for the safety risks flagged.';
            }
            if (formData.previous_support_choice === 'Yes' && !formData.previous_support_details.trim()) {
                return 'Please describe your previous support details since you checked "Yes".';
            }
        }
        if (step === 5) {
            if (!formData.readiness1 || !formData.readiness2 || !formData.readiness3 || !formData.readiness4) {
                return 'Please review and check all virtual session readiness requirements.';
            }
            if (!formData.consent_name.trim()) return 'Consent Name is required.';
            if (!formData.signature.trim()) return 'Your signature (typed name) is required.';
        }
        return '';
    };

    const handleNext = () => {
        const error = validateStep();
        if (error) {
            alert(error);
            return;
        }
        setStep(prev => prev + 1);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleBack = () => {
        setStep(prev => prev - 1);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const isSafetyTriggered = formData.self_harm === 'Yes' || 
                              formData.harm_others === 'Yes' || 
                              formData.unsafe === 'Yes' || 
                              formData.abuse === 'Yes';

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        const error = validateStep();
        if (error) {
            alert(error);
            return;
        }

        setIsSubmitting(true);
        setSubmitError('');

        const submissionPayload = {
            ...formData,
            support_needed_list: [
                ...formData.support,
                formData.support_other ? `Other: ${formData.support_other}` : null
            ].filter(Boolean).join(', '),
            wellbeing_symptoms_list: formData.wellbeing_symptoms.join(', '),
            virtual_readiness: [
                formData.readiness1 ? 'Private space available' : null,
                formData.readiness2 ? 'Reliable internet/phone' : null,
                formData.readiness3 ? 'Not driving during sessions' : null,
                formData.readiness4 ? 'Understand confidentiality limits' : null
            ].filter(Boolean).join(', ')
        };

        if (isPlaceholderId) {
            setTimeout(() => {
                setIsSubmitting(false);
                setSubmitSuccess(true);
                localStorage.removeItem('pameltex_intake_draft');
            }, 1500);
            return;
        }

        try {
            const response = await fetch(`https://formspree.io/f/${formspreeId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(submissionPayload)
            });

            if (response.ok) {
                setSubmitSuccess(true);
                localStorage.removeItem('pameltex_intake_draft');
            } else {
                const responseData = await response.json();
                throw new Error(responseData.error || 'Failed to submit form.');
            }
        } catch (err) {
            console.error('Submission error:', err);
            setSubmitError(err.message || 'An error occurred during submission. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const progressPercent = ((step - 1) / 4) * 100;

    return (
        <>
            <SEO
                title="Virtual Therapy Client Intake Form"
                description="Securely submit your virtual therapy intake details to Foundations Counselling Academy and Pameltex Psychosocial Services."
            />

            <div className="intake-page">
                <section className="intake-hero">
                    <div className="container-x">
                        <span className="intake-badge">Therapy Portal</span>
                        <h1>Client Intake Form</h1>
                        <p>Foundations Counselling Academy / Pameltex Psychosocial & Counselling Services</p>
                    </div>
                </section>

                <section className="intake-body-section py-12">
                    <div className="intake-container">
                        
                        {isPlaceholderId && !submitSuccess && (
                            <div className="intake-demo-banner">
                                <div className="banner-content">
                                    <span className="banner-icon">⚙️</span>
                                    <div>
                                        <strong>Intake Form Sandbox Mode</strong>
                                        <p>Submissions will be simulated locally. Add <code>VITE_FORMSPREE_ID</code> to your <code>.env</code> file for live email notifications.</p>
                                    </div>
                                </div>
                                <button type="button" className="demo-autofill-btn" onClick={handleAutofillDemo}>
                                    ⚡ Autofill Demo Data
                                </button>
                            </div>
                        )}

                        {submitSuccess ? (
                            <div className="intake-success-card">
                                <div className="success-icon-wrap">
                                    <svg viewBox="0 0 24 24" className="success-svg">
                                        <path fill="currentColor" d="M12,2C6.48,2,2,6.48,2,12s4.48,10,10,10,10-4.48,10-10S17.52,2,12,2Zm-2,15l-5-5,1.41-1.41,3.59,3.59,7.59-7.59,1.41,1.41-9,9Z" />
                                    </svg>
                                </div>
                                <h2>Intake Form Submitted Successfully!</h2>
                                <p>Thank you for taking the time to share your details. Your intake form has been processed securely. Our administrative team will review your file and get in touch with you shortly to schedule or confirm your virtual consultation.</p>
                                
                                {isPlaceholderId && (
                                    <div className="demo-data-receipt">
                                        <h4>Submitted Details (Simulation Sandbox)</h4>
                                        <ul>
                                            <li><strong>Client:</strong> {formData.full_name} ({formData.gender || 'Not specified'})</li>
                                            <li><strong>Email:</strong> {formData.email}</li>
                                            <li><strong>Phone:</strong> {formData.phone}</li>
                                            <li><strong>Contact Method:</strong> {formData.contact_method}</li>
                                            <li><strong>Support:</strong> {formData.support.join(', ')}</li>
                                            <li><strong>Safety Screening Flags:</strong> Self-Harm: {formData.self_harm}, Harm Others: {formData.harm_others}, Unsafe: {formData.unsafe}, Abuse: {formData.abuse}</li>
                                        </ul>
                                    </div>
                                )}

                                <div className="success-actions">
                                    <Link to="/contact" className="btn-primary">Book a Session</Link>
                                    <Link to="/" className="btn-ghost" style={{ marginLeft: '10px' }}>Return to Homepage</Link>
                                </div>
                            </div>
                        ) : (
                            <div className="intake-form-wrapper">
                                <div className="intake-progress-card">
                                    <div className="progress-bar-container">
                                        <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }}></div>
                                    </div>
                                    <div className="steps-indicators">
                                        <div className={`step-node ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
                                            <div className="node-number">{step > 1 ? '✓' : '1'}</div>
                                            <span className="node-label">Details</span>
                                        </div>
                                        <div className={`step-node ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
                                            <div className="node-number">{step > 2 ? '✓' : '2'}</div>
                                            <span className="node-label">Emergency</span>
                                        </div>
                                        <div className={`step-node ${step >= 3 ? 'active' : ''} ${step > 3 ? 'completed' : ''}`}>
                                            <div className="node-number">{step > 3 ? '✓' : '3'}</div>
                                            <span className="node-label">Therapy</span>
                                        </div>
                                        <div className={`step-node ${step >= 4 ? 'active' : ''} ${step > 4 ? 'completed' : ''}`}>
                                            <div className="node-number">{step > 4 ? '✓' : '4'}</div>
                                            <span className="node-label">Screening</span>
                                        </div>
                                        <div className={`step-node ${step >= 5 ? 'active' : ''}`}>
                                            <div className="node-number">5</div>
                                            <span className="node-label">Consent</span>
                                        </div>
                                    </div>
                                </div>

                                <form onSubmit={handleSubmit} className="intake-form-card" key={step}>
                                    
                                    {step === 1 && (
                                        <div className="form-step-content">
                                            <div className="step-header">
                                                <span className="step-count">Step 1 of 5</span>
                                                <h2>Personal & Contact Details</h2>
                                                <p>Please provide your basic contact and demographic information.</p>
                                            </div>

                                            <div className="form-grid">
                                                <div className="form-group full-width">
                                                    <label htmlFor="full_name">Full Name <span className="required-star">*</span></label>
                                                    <input 
                                                        type="text" 
                                                        id="full_name"
                                                        value={formData.full_name} 
                                                        onChange={(e) => updateFormData({ full_name: e.target.value })}
                                                        placeholder="e.g. John Doe"
                                                        required 
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="dob">Date of Birth</label>
                                                    <input 
                                                        type="date" 
                                                        id="dob"
                                                        value={formData.dob} 
                                                        onChange={handleDobChange} 
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="age">Age</label>
                                                    <input 
                                                        type="number" 
                                                        id="age"
                                                        value={formData.age} 
                                                        onChange={(e) => updateFormData({ age: e.target.value })}
                                                        placeholder="Auto-calculated"
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="gender">Gender</label>
                                                    <input 
                                                        type="text" 
                                                        id="gender"
                                                        value={formData.gender} 
                                                        onChange={(e) => updateFormData({ gender: e.target.value })}
                                                        placeholder="e.g. Female, Male, Non-binary" 
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="phone">Phone Number <span className="required-star">*</span></label>
                                                    <input 
                                                        type="tel" 
                                                        id="phone"
                                                        value={formData.phone} 
                                                        onChange={(e) => updateFormData({ phone: e.target.value })}
                                                        placeholder="e.g. +267 72 123 456" 
                                                        required
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="email">Email Address <span className="required-star">*</span></label>
                                                    <input 
                                                        type="email" 
                                                        id="email"
                                                        value={formData.email} 
                                                        onChange={(e) => updateFormData({ email: e.target.value })}
                                                        placeholder="e.g. john@example.com" 
                                                        required
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="location">Physical Location / City</label>
                                                    <input 
                                                        type="text" 
                                                        id="location"
                                                        value={formData.location} 
                                                        onChange={(e) => updateFormData({ location: e.target.value })}
                                                        placeholder="e.g. Gaborone, Botswana" 
                                                    />
                                                </div>

                                                <div className="form-group full-width">
                                                    <label htmlFor="contact_method">Preferred Method of Contact</label>
                                                    <select 
                                                        id="contact_method"
                                                        value={formData.contact_method} 
                                                        onChange={(e) => updateFormData({ contact_method: e.target.value })}
                                                    >
                                                        <option value="Phone call">Phone call</option>
                                                        <option value="WhatsApp">WhatsApp</option>
                                                        <option value="Email">Email</option>
                                                        <option value="SMS">SMS</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {step === 2 && (
                                        <div className="form-step-content">
                                            <div className="step-header">
                                                <span className="step-count">Step 2 of 5</span>
                                                <h2>Emergency Contact</h2>
                                                <p>In line with ethical therapy guidelines, we require emergency contact details for safety purposes.</p>
                                            </div>

                                            <div className="form-grid">
                                                <div className="form-group full-width">
                                                    <label htmlFor="emergency_name">Contact Name <span className="required-star">*</span></label>
                                                    <input 
                                                        type="text" 
                                                        id="emergency_name"
                                                        value={formData.emergency_name} 
                                                        onChange={(e) => updateFormData({ emergency_name: e.target.value })}
                                                        placeholder="Full name of emergency contact"
                                                        required 
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="emergency_relationship">Relationship</label>
                                                    <input 
                                                        type="text" 
                                                        id="emergency_relationship"
                                                        value={formData.emergency_relationship} 
                                                        onChange={(e) => updateFormData({ emergency_relationship: e.target.value })}
                                                        placeholder="e.g. Spouse, Parent, Sibling, Friend" 
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label htmlFor="emergency_phone">Phone Number <span className="required-star">*</span></label>
                                                    <input 
                                                        type="tel" 
                                                        id="emergency_phone"
                                                        value={formData.emergency_phone} 
                                                        onChange={(e) => updateFormData({ emergency_phone: e.target.value })}
                                                        placeholder="Emergency phone number"
                                                        required 
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {step === 3 && (
                                        <div className="form-step-content">
                                            <div className="step-header">
                                                <span className="step-count">Step 3 of 5</span>
                                                <h2>Reason for Seeking Support</h2>
                                                <p>Help us understand your therapeutic goals and what type of support matches your current situation.</p>
                                            </div>

                                            <div className="form-group">
                                                <div className="textarea-label-wrapper">
                                                    <label htmlFor="reason">Why are you seeking therapy at this time? <span className="required-star">*</span></label>
                                                    <span className="char-count">{formData.reason.length} characters</span>
                                                </div>
                                                <textarea 
                                                    id="reason"
                                                    rows="5"
                                                    value={formData.reason} 
                                                    onChange={(e) => updateFormData({ reason: e.target.value })}
                                                    placeholder="Describe what has been going on, any specific events, feelings, or objectives you would like to address..."
                                                    required
                                                ></textarea>
                                            </div>

                                            <div className="form-group" style={{ marginTop: '25px' }}>
                                                <label style={{ marginBottom: '15px', display: 'block' }}>Type of Support Needed <span className="required-star">*</span> <small style={{ fontWeight: 'normal', color: '#666' }}>(Select all that apply)</small></label>
                                                
                                                <div className="checkbox-grid">
                                                    {[
                                                        'Individual counselling',
                                                        'Couples counselling',
                                                        'Family support',
                                                        'Work stress',
                                                        'Grief',
                                                        'Anxiety',
                                                        'Relationships',
                                                        'Growth'
                                                    ].map((item) => {
                                                        const labelMap = {
                                                            'Individual counselling': 'Individual counselling',
                                                            'Couples counselling': 'Couples counselling',
                                                            'Family support': 'Family support',
                                                            'Work stress': 'Work-related stress',
                                                            'Grief': 'Grief or loss',
                                                            'Anxiety': 'Anxiety or stress management',
                                                            'Relationships': 'Relationship challenges',
                                                            'Growth': 'Personal growth / life coaching'
                                                        };
                                                        const isChecked = formData.support.includes(item);
                                                        return (
                                                            <div 
                                                                key={item} 
                                                                className={`checkbox-card ${isChecked ? 'checked' : ''}`}
                                                                onClick={() => handleSupportCheckbox(item)}
                                                            >
                                                                <div className="checkbox-ui">
                                                                    {isChecked && <span className="check-mark">✓</span>}
                                                                </div>
                                                                <span className="checkbox-label">{labelMap[item]}</span>
                                                            </div>
                                                        );
                                                    })}
                                                </div>

                                                <div className="form-group" style={{ marginTop: '20px' }}>
                                                    <label htmlFor="support_other">Other (please specify):</label>
                                                    <input 
                                                        type="text" 
                                                        id="support_other"
                                                        value={formData.support_other} 
                                                        onChange={(e) => updateFormData({ support_other: e.target.value })}
                                                        placeholder="e.g. Group therapy, trauma support, etc."
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {step === 4 && (
                                        <div className="form-step-content">
                                            <div className="step-header">
                                                <span className="step-count">Step 4 of 5</span>
                                                <h2>Wellbeing & Safety Screening</h2>
                                                <p>Your safety is very important to us. Please answer these screening questions honestly so we can support you appropriately.</p>
                                            </div>

                                            <div className="form-group">
                                                <label style={{ marginBottom: '15px', display: 'block' }}>Current Emotional Wellbeing <span className="required-star">*</span> <small style={{ fontWeight: 'normal', color: '#666' }}>(Over the past two weeks, have you experienced any of the following? Select all that apply)</small></label>
                                                
                                                <div className="checkbox-grid" style={{ marginBottom: '25px' }}>
                                                    {[
                                                        'Persistent sadness',
                                                        'Anxiety or panic',
                                                        'Sleep difficulties',
                                                        'Anger or irritability',
                                                        'Loss of motivation',
                                                        'Relationship conflict',
                                                        'Work-related pressure',
                                                        'Grief or major life change',
                                                        'None of the above'
                                                    ].map((item) => {
                                                        const isChecked = formData.wellbeing_symptoms.includes(item);
                                                        return (
                                                            <div 
                                                                key={item} 
                                                                className={`checkbox-card ${isChecked ? 'checked' : ''}`}
                                                                onClick={() => handleWellbeingCheckbox(item)}
                                                            >
                                                                <div className="checkbox-ui">
                                                                    {isChecked && <span className="check-mark">✓</span>}
                                                                </div>
                                                                <span className="checkbox-label">{item}</span>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>

                                            <div className="screening-questions" style={{ marginTop: '25px' }}>
                                                <h3>Safety & Risk Screening</h3>
                                                <p style={{ fontSize: '13px', color: '#666', marginTop: '-15px', marginBottom: '20px' }}>This section helps us understand whether urgent support may be needed.</p>
                                                
                                                <div className="select-row-grid">
                                                    <div className="form-group select-group">
                                                        <label htmlFor="self_harm">Thoughts of self-harm?</label>
                                                        <select 
                                                            id="self_harm"
                                                            value={formData.self_harm} 
                                                            onChange={(e) => updateFormData({ self_harm: e.target.value })}
                                                            className={formData.self_harm === 'Yes' ? 'risk-yes' : ''}
                                                        >
                                                            <option value="No">No</option>
                                                            <option value="Yes">Yes</option>
                                                        </select>
                                                    </div>

                                                    <div className="form-group select-group">
                                                        <label htmlFor="harm_others">Thoughts of harming others?</label>
                                                        <select 
                                                            id="harm_others"
                                                            value={formData.harm_others} 
                                                            onChange={(e) => updateFormData({ harm_others: e.target.value })}
                                                            className={formData.harm_others === 'Yes' ? 'risk-yes' : ''}
                                                        >
                                                            <option value="No">No</option>
                                                            <option value="Yes">Yes</option>
                                                        </select>
                                                    </div>

                                                    <div className="form-group select-group">
                                                        <label htmlFor="unsafe">Feeling unsafe in home/relationship/environment?</label>
                                                        <select 
                                                            id="unsafe"
                                                            value={formData.unsafe} 
                                                            onChange={(e) => updateFormData({ unsafe: e.target.value })}
                                                            className={formData.unsafe === 'Yes' ? 'risk-yes' : ''}
                                                        >
                                                            <option value="No">No</option>
                                                            <option value="Yes">Yes</option>
                                                        </select>
                                                    </div>

                                                    <div className="form-group select-group">
                                                        <label htmlFor="abuse">Exposure to abuse, violence, or threats?</label>
                                                        <select 
                                                            id="abuse"
                                                            value={formData.abuse} 
                                                            onChange={(e) => updateFormData({ abuse: e.target.value })}
                                                            className={formData.abuse === 'Yes' ? 'risk-yes' : ''}
                                                        >
                                                            <option value="No">No</option>
                                                            <option value="Yes">Yes</option>
                                                        </select>
                                                    </div>
                                                </div>

                                                {isSafetyTriggered && (
                                                    <div className="intake-safety-alert">
                                                        <div className="alert-badge">⚠️ IMMEDIATE SUPPORT RESOURCES</div>
                                                        <p>If you are experiencing suicidal thoughts, self-harm impulses, feeling unsafe in your environment, or dealing with immediate abuse, please note that virtual therapy might need to be supplemented with emergency services. You can reach out to these crisis resources in Botswana immediately:</p>
                                                        <div className="helpline-subgrid">
                                                            <div className="helpline-item">
                                                                <strong>Police Emergency</strong>
                                                                <a href="tel:999">📞 999</a>
                                                            </div>
                                                            <div className="helpline-item">
                                                                <strong>Mobile Networks Emergency</strong>
                                                                <a href="tel:112">📞 112</a>
                                                            </div>
                                                            <div className="helpline-item">
                                                                <strong>GBV Tele-Counselling</strong>
                                                                <a href="tel:14655">📞 14655</a>
                                                            </div>
                                                            <div className="helpline-item">
                                                                <strong>Police GBV Toll-Free</strong>
                                                                <a href="tel:0800600144">📞 0800 600 144</a>
                                                            </div>
                                                        </div>
                                                        <p style={{ marginTop: '10px', fontSize: '12px', opacity: 0.8 }}>For details, view our <Link to="/contact" target="_blank" style={{ textDecoration: 'underline', color: 'inherit', fontWeight: 'bold' }}>Emergency Resources Page</Link>.</p>
                                                    </div>
                                                )}

                                                <div className="form-group" style={{ marginTop: '15px' }}>
                                                    <label htmlFor="risk_details">Explain if "Yes" {isSafetyTriggered && <span className="required-star">*</span>}</label>
                                                    <textarea 
                                                        id="risk_details"
                                                        rows="3"
                                                        value={formData.risk_details} 
                                                        onChange={(e) => updateFormData({ risk_details: e.target.value })}
                                                        placeholder="Please describe details of the safety concerns marked above, so we can support your wellbeing safely..."
                                                        required={isSafetyTriggered}
                                                    ></textarea>
                                                </div>
                                            </div>

                                            <div className="previous-support-section" style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid #eee' }}>
                                                <h3>Previous Support & Medications</h3>
                                                
                                                <div className="form-group select-group" style={{ maxWidth: '300px', marginBottom: '15px' }}>
                                                    <label htmlFor="previous_support_choice">Have you received counselling, therapy, psychiatric, or psychological support before? <span className="required-star">*</span></label>
                                                    <select 
                                                        id="previous_support_choice"
                                                        value={formData.previous_support_choice} 
                                                        onChange={(e) => updateFormData({ previous_support_choice: e.target.value })}
                                                    >
                                                        <option value="No">No</option>
                                                        <option value="Yes">Yes</option>
                                                    </select>
                                                </div>

                                                {formData.previous_support_choice === 'Yes' && (
                                                    <div className="form-group">
                                                        <label htmlFor="previous_support_details">Please describe previous support details <span className="required-star">*</span></label>
                                                        <textarea 
                                                            id="previous_support_details"
                                                            rows="3"
                                                            value={formData.previous_support_details} 
                                                            onChange={(e) => updateFormData({ previous_support_details: e.target.value })}
                                                            placeholder="Details of previous therapy, dates, outcomes..."
                                                            required
                                                        ></textarea>
                                                    </div>
                                                )}

                                                <div className="form-group select-group" style={{ maxWidth: '300px', marginTop: '15px' }}>
                                                    <label htmlFor="medication">Are you currently taking any psychiatric medications?</label>
                                                    <select 
                                                        id="medication"
                                                        value={formData.medication} 
                                                        onChange={(e) => updateFormData({ medication: e.target.value })}
                                                    >
                                                        <option value="No">No</option>
                                                        <option value="Yes">Yes</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {step === 5 && (
                                        <div className="form-step-content">
                                            <div className="step-header">
                                                <span className="step-count">Step 5 of 5</span>
                                                <h2>Consent & Digital Signature</h2>
                                                <p>Please review and confirm your readiness for virtual therapy and provide your consent.</p>
                                            </div>

                                            <div className="readiness-section">
                                                <h3>Virtual Session Readiness</h3>
                                                <p style={{ fontSize: '13px', color: '#666', marginTop: '-15px', marginBottom: '20px' }}>Please check all statements to confirm your readiness.</p>
                                                
                                                <div className="checkbox-list">
                                                    <div 
                                                        className={`checkbox-card ${formData.readiness1 ? 'checked' : ''}`}
                                                        onClick={() => updateFormData({ readiness1: !formData.readiness1 })}
                                                    >
                                                        <div className="checkbox-ui">
                                                            {formData.readiness1 && <span className="check-mark">✓</span>}
                                                        </div>
                                                        <span className="checkbox-label">I have a private space where I will not be interrupted during sessions.</span>
                                                    </div>

                                                    <div 
                                                        className={`checkbox-card ${formData.readiness2 ? 'checked' : ''}`}
                                                        onClick={() => updateFormData({ readiness2: !formData.readiness2 })}
                                                    >
                                                        <div className="checkbox-ui">
                                                            {formData.readiness2 && <span className="check-mark">✓</span>}
                                                        </div>
                                                        <span className="checkbox-label">I have access to a reliable internet connection or telephone line.</span>
                                                    </div>

                                                    <div 
                                                        className={`checkbox-card ${formData.readiness3 ? 'checked' : ''}`}
                                                        onClick={() => updateFormData({ readiness3: !formData.readiness3 })}
                                                    >
                                                        <div className="checkbox-ui">
                                                            {formData.readiness3 && <span className="check-mark">✓</span>}
                                                        </div>
                                                        <span className="checkbox-label">I agree not to drive or operate machinery during virtual sessions.</span>
                                                    </div>

                                                    <div 
                                                        className={`checkbox-card ${formData.readiness4 ? 'checked' : ''}`}
                                                        onClick={() => updateFormData({ readiness4: !formData.readiness4 })}
                                                    >
                                                        <div className="checkbox-ui">
                                                            {formData.readiness4 && <span className="check-mark">✓</span>}
                                                        </div>
                                                        <span className="checkbox-label">I understand the limits of confidentiality in virtual settings.</span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="consent-section" style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid #eee' }}>
                                                <h3>Client Consent</h3>
                                                <p style={{ fontSize: '13px', color: '#666', marginTop: '-10px', marginBottom: '20px' }}>By signing below, you consent to receive virtual therapy services.</p>
                                                
                                                <div className="form-grid">
                                                    <div className="form-group full-width">
                                                        <label htmlFor="consent_name">Consent Name (Full Name) <span className="required-star">*</span></label>
                                                        <input 
                                                            type="text" 
                                                            id="consent_name"
                                                            value={formData.consent_name} 
                                                            onChange={(e) => updateFormData({ consent_name: e.target.value })}
                                                            placeholder="Type your full name to consent"
                                                            required 
                                                        />
                                                    </div>

                                                    <div className="form-group">
                                                        <label htmlFor="signature">Signature (Typed Name) <span className="required-star">*</span></label>
                                                        <input 
                                                            type="text" 
                                                            id="signature"
                                                            value={formData.signature} 
                                                            onChange={(e) => updateFormData({ signature: e.target.value })}
                                                            placeholder="Type your signature"
                                                            required 
                                                        />
                                                    </div>

                                                    <div className="form-group">
                                                        <label htmlFor="consent_date">Consent Date</label>
                                                        <input 
                                                            type="date" 
                                                            id="consent_date"
                                                            value={formData.consent_date} 
                                                            onChange={(e) => updateFormData({ consent_date: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {submitError && (
                                        <div className="intake-error-message">
                                            <strong>Error:</strong> {submitError}
                                        </div>
                                    )}

                                    <div className="form-actions-row">
                                        {step > 1 && (
                                            <button 
                                                type="button" 
                                                className="btn-ghost" 
                                                onClick={handleBack}
                                            >
                                                Back
                                            </button>
                                        )}
                                        <div style={{ marginLeft: 'auto' }}>
                                            {step < 5 ? (
                                                <button 
                                                    type="button" 
                                                    className="btn-primary" 
                                                    onClick={handleNext}
                                                >
                                                    Next Step
                                                </button>
                                            ) : (
                                                <button 
                                                    type="submit" 
                                                    className="btn-primary"
                                                    disabled={isSubmitting}
                                                >
                                                    {isSubmitting ? 'Submitting...' : 'Submit Intake Form'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </form>
                            </div>
                        )}
                    </div>
                </section>
            </div>
        </>
    );
};

export default IntakeForm;
