import React, { useRef, useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import MessageItem from './MessageItem';

export default function ChatArea() {
  const { messages, addMessage, user, step, setStep, setWizardDraft, wizardDraft, resetSession } = useApp();
  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef(null);

  // Auto-scroll à chaque nouveau message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim()) return;
    
    // ======= STEP: ATTENTE DU NOM =======
    if (step === 'WAIT_NAME') {
      const nameGiven = inputValue.trim();
      addMessage({ type: 'text', sender: 'user', text: nameGiven });
      setInputValue('');
      setWizardDraft(prev => ({ ...prev, exName: nameGiven }));
      
      // Typing indicator
      addMessage({ type: 'typing', sender: 'bot' });
      
      setTimeout(() => {
        setStep('WAIT_SECTIONS');

        if (wizardDraft.sections && wizardDraft.sections.length > 0) {
          // On a des sections détectées → on affiche les checkboxes
          addMessage({ 
            type: 'sections', 
            sender: 'bot', 
            sections: wizardDraft.sections
          });
        } else {
          // Aucune section détectable → cours complet, passer directement aux difficultés
          setWizardDraft(prev => ({ ...prev, selSections: [{ num: '', title: 'Cours complet', content: wizardDraft.courseText || '' }] }));
          addMessage({ 
            type: 'text', 
            sender: 'bot', 
            text: `Aucune section numérotée détectée — je créerai des exercices sur l'ensemble du cours.<br><br>Quel niveau de difficulté souhaitez-vous ?`,
            html: true 
          });
          addMessage({ type: 'difficulty', sender: 'bot' });
          setStep('WAIT_DIFF');
        }
      }, 800);
      return;
    }

    // ======= STEP: DÉFAUT (message libre) =======
    addMessage({ type: 'text', sender: 'user', text: inputValue });
    setInputValue('');
    
    // Réponse générique du bot
    setTimeout(() => {
      addMessage({ type: 'text', sender: 'bot', text: 'Utilisez les options ou boutons proposés. Vous pouvez aussi analyser un nouveau cours. 😊' });
    }, 500);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  // Filtrer les "typing" obsolètes (si un message est arrivé après)
  const displayMessages = messages.filter((m, i, arr) => {
    if (m.type === 'typing' && i < arr.length - 1) return false;
    return true;
  });

  const showRestart = step !== 'IDLE' && step !== 'DONE';

  return (
    <main className="chat-area">
      {showRestart && (
        <div className="restart-bar">
          <span>Étape en cours : <strong>{
            step === 'WAIT_NAME' ? 'Nommage' :
            step === 'WAIT_SECTIONS' ? 'Sélection des sections' :
            step === 'WAIT_DIFF' ? 'Niveau de difficulté' :
            'Validation'
          }</strong></span>
          <button className="restart-btn" onClick={resetSession}>
            ↺ Recommencer depuis le début
          </button>
        </div>
      )}
      <div className="chat-msgs">
        {/* Message d'accueil (visible uniquement s'il n'y a aucun message) */}
        {displayMessages.length === 0 && (
          <div className="mrow bot">
            <div className="mavatar bot">PB</div>
            <div className="mbubble" dangerouslySetInnerHTML={{__html: `Bonjour <strong>${user}</strong> ! Je suis <strong>PédaBot</strong>, votre assistant de consolidation pédagogique.<br><br>
              Je vais vous guider étape par étape pour créer des exercices adaptés à votre cours.<br><br>
              Commencez par <strong>saisir ou coller votre cours</strong> dans le panneau de gauche, puis cliquez sur <strong>"Analyser le cours"</strong>.`}}></div>
          </div>
        )}

        {displayMessages.map((msg, i) => (
          <MessageItem key={`${msg.type}-${i}`} msg={msg} />
        ))}
        
        <div ref={chatEndRef} />
      </div>

      <div className="chat-bar">
        <input 
          className="chat-in" 
          type="text" 
          placeholder="Votre réponse..." 
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="send-btn" onClick={handleSend} title="Envoyer">
          <svg viewBox="0 0 24 24">
            <path d="M22 2L11 13" stroke="white" strokeWidth="2" fill="none" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" fill="white"/>
          </svg>
        </button>
      </div>
    </main>
  );
}
