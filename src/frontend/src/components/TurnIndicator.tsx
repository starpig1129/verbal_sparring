type Props = { isMyTurn: boolean }

export default function TurnIndicator({ isMyTurn }: Props) {
  return (
    <div className={`py-2.5 px-4 text-center font-mono text-xs md:text-sm tracking-[3px] border-t border-b flex-shrink-0 font-bold ${
      isMyTurn
        ? 'bg-[#3a1a00]/40 border-[#ff4400]/30 text-vermillion shadow-[inset_0_0_12px_rgba(204,51,0,0.05)]'
        : 'bg-[#14100b] border-[#4a3f28] text-[#a88a6d]'
    }`}>
      {isMyTurn ? '⚔ 輪到你出招！⚔' : '等待對手...'}
    </div>
  )
}
