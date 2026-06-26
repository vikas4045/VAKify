import { useState, type ReactNode } from 'react';
import { ChevronRight, BookOpen, CheckCircle2, Code2, FileText, Mail, Phone } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { AssessmentWizard } from './AssessmentWizard';

const LANGUAGE_CHOICES = ['Python', 'JavaScript', 'Java', 'C++', 'C'];

export function Onboarding() {
  const { user, completeOnboarding } = useAuth();
  const [step, setStep] = useState(1);
  const [selectedLanguage, setSelectedLanguage] = useState(user?.preferredLanguage || '');
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otherDetails, setOtherDetails] = useState('');
  const [finishing, setFinishing] = useState(false);

  const totalSteps = 3;
  const currentLearningStyle = user?.learningStyle || 'visual';

  const canFinish = Boolean(
    displayName.trim() &&
      email.trim() &&
      selectedLanguage &&
      !finishing,
  );

  const finishOnboarding = async () => {
    if (!canFinish) {
      return;
    }

    setFinishing(true);
    try {
      await completeOnboarding({
        displayName: displayName.trim(),
        email: email.trim(),
        preferredLanguage: selectedLanguage,
        phoneNumber: phoneNumber.trim(),
        otherDetails: otherDetails.trim() ? { notes: otherDetails.trim() } : null,
      });
    } finally {
      setFinishing(false);
    }
  };

  const renderStepHeader = (title: string, description: string, icon: ReactNode) => (
    <div className="flex items-center gap-3 mb-6">
      <div className="w-12 h-12 rounded-full bg-secondary/10 flex items-center justify-center">
        {icon}
      </div>
      <div>
        <h2 className="text-2xl">{title}</h2>
        <p className="text-muted-foreground">{description}</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-5xl">
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div
                key={i}
                className={`h-2 flex-1 rounded-full ${i + 1 <= step ? 'bg-secondary' : 'bg-muted'}`}
              />
            ))}
          </div>
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              Step {step} of {totalSteps}
            </p>
            <p className="text-sm text-muted-foreground">Create your account, learn your style, and launch into Vakify.</p>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 sm:p-8 shadow-sm">
          {step === 1 && (
            <AssessmentWizard
              title="Vakify assessment"
              description="Take the 20-question style assessment now, or skip it and come back later from your dashboard."
              showSkip
              skipLabel="Skip for now"
              continueLabel="Continue to Language"
              onCompleted={async () => {
                setStep(2);
              }}
              onSkip={() => setStep(2)}
            />
          )}

          {step === 2 && (
            <div className="space-y-6">
              {renderStepHeader(
                'Choose your programming language',
                'Vakify will tailor tasks, labs, and code examples to this language.',
                <Code2 className="w-6 h-6 text-secondary" />,
              )}

              <div className="rounded-2xl border border-secondary/20 bg-secondary/5 p-5">
                <div className="flex items-center gap-2 text-secondary">
                  <CheckCircle2 className="h-5 w-5" />
                  <span className="font-medium">Learning style ready</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {user?.learningStyle
                    ? (
                      <>
                        Your current learning style is{' '}
                        <span className="font-medium text-foreground capitalize">{currentLearningStyle}</span>. You can retake the assessment later from the dashboard.
                      </>
                    )
                    : 'You can skip the assessment now and take it later from the dashboard when you are ready.'}
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {LANGUAGE_CHOICES.map((lang) => {
                  const selected = selectedLanguage === lang;
                  return (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => setSelectedLanguage(lang)}
                      className={`rounded-xl border px-4 py-4 text-left transition-all ${
                        selected
                          ? 'border-secondary bg-secondary/5 shadow-sm'
                          : 'border-border bg-background hover:border-secondary/50'
                      }`}
                    >
                      <div className="text-base font-medium">{lang}</div>
                      <div className="mt-1 text-xs text-muted-foreground">Daily tasks and labs in {lang}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              {renderStepHeader(
                'Complete your profile',
                'Add the details Vakify uses to personalize your dashboard and support.',
                <BookOpen className="w-6 h-6 text-secondary" />,
              )}

              <div className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
                <div className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm mb-2">Full Name</label>
                      <input
                        type="text"
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        className="w-full px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                        placeholder="Enter your name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm mb-2">Email</label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full pl-11 pr-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                          placeholder="Enter your email"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm mb-2">Phone Number</label>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                        <input
                          type="tel"
                          value={phoneNumber}
                          onChange={(e) => setPhoneNumber(e.target.value)}
                          className="w-full pl-11 pr-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                          placeholder="Enter your phone number"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm mb-2">Chosen Language</label>
                      <input
                        type="text"
                        value={selectedLanguage}
                        readOnly
                        className="w-full px-4 py-3 rounded-lg border border-border bg-muted/40 text-foreground"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm mb-2">Other Details</label>
                    <textarea
                      value={otherDetails}
                      onChange={(e) => setOtherDetails(e.target.value)}
                      className="w-full min-h-36 px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                      placeholder="Tell Vakify about your goals, current level, school, college, or anything else you want us to know."
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-muted/20 p-5 space-y-4">
                  <div className="flex items-center gap-2 text-secondary">
                    <CheckCircle2 className="h-5 w-5" />
                    <span className="font-medium">Your setup summary</span>
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="rounded-xl border border-border bg-background px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Learning style</div>
                      <div className="mt-1 text-base capitalize">{currentLearningStyle}</div>
                    </div>
                    <div className="rounded-xl border border-border bg-background px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Programming language</div>
                      <div className="mt-1 text-base">{selectedLanguage || 'Not selected yet'}</div>
                    </div>
                    <div className="rounded-xl border border-border bg-background px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Profile details</div>
                      <div className="mt-1 text-base">{displayName || 'Your name'} · {email || 'your@email.com'}</div>
                    </div>
                    <div className="rounded-xl border border-border bg-background px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">What happens next</div>
                      <div className="mt-1 text-base">We’ll open your dashboard with language-aware tasks and labs.</div>
                    </div>
                  </div>
                  <div className="rounded-xl border border-border bg-secondary/5 px-4 py-3 text-sm text-muted-foreground">
                    <FileText className="inline-block mr-2 h-4 w-4 text-secondary" />
                    You can change your profile details later in Settings.
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-col-reverse sm:flex-row gap-3 mt-8">
            {step > 1 && (
              <button
                onClick={() => setStep(step - 1)}
                className="px-6 py-3 rounded-lg border border-border hover:bg-muted transition-colors"
              >
                Back
              </button>
            )}
            {step === 1 ? null : (
            <button
              onClick={async () => {
                if (step === 2) {
                  if (selectedLanguage) {
                    setStep(3);
                  }
                  return;
                }
                await finishOnboarding();
              }}
              disabled={
                (step === 2 && !selectedLanguage) ||
                (step === 3 && !canFinish)
              }
              className="flex-1 bg-primary text-primary-foreground py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {step === 2 && 'Continue to Profile'}
              {step === 3 && (finishing ? 'Finishing...' : 'Get Started')}
              <ChevronRight className="w-5 h-5" />
            </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
